const $ = id => document.getElementById(id);

let rec = null;
let timer = null;
let seconds = 0;
let recordedBlob = null;


// ===============================
// Recording Timer
// ===============================
function tick() {
  seconds++;

  $("timer").textContent =
    String(Math.floor(seconds / 60)).padStart(2, "0") +
    ":" +
    String(seconds % 60).padStart(2, "0");
}


// ===============================
// Start Microphone Recording
// ===============================
async function startRecording() {

  const stream = await navigator.mediaDevices.getUserMedia({
    audio: true
  });

  const ctx = new AudioContext();

  const source = ctx.createMediaStreamSource(stream);

  const processor = ctx.createScriptProcessor(
    4096,
    1,
    1
  );

  const data = [];

  source.connect(processor);
  processor.connect(ctx.destination);

  processor.onaudioprocess = e => {

    const input = e.inputBuffer.getChannelData(0);

    data.push(new Float32Array(input));
  };

  $("recordBtn").textContent = "■ Stop recording";
  $("recordBtn").classList.add("recording");

  $("recordState").textContent = "Recording…";

  seconds = 0;

  $("timer").textContent = "00:00";

  timer = setInterval(tick, 1000);

  rec = {
    stream,
    ctx,
    processor,
    data,
    sampleRate: ctx.sampleRate
  };
}


// ===============================
// Convert Microphone Audio → WAV
// ===============================
function floatToWav(chunks, sampleRate) {

  // Calculate total number of samples
  const length = chunks.reduce(
    (total, chunk) => total + chunk.length,
    0
  );

  // Combine all recorded chunks
  const samples = new Float32Array(length);

  let offset = 0;

  for (const chunk of chunks) {

    samples.set(chunk, offset);

    offset += chunk.length;
  }


  // WAV = 44 byte header + PCM data
  const bytesPerSample = 2;

  const dataSize =
    samples.length * bytesPerSample;

  const buffer =
    new ArrayBuffer(44 + dataSize);

  const view =
    new DataView(buffer);


  // Write text into WAV header
  function writeString(offset, text) {

    for (let i = 0; i < text.length; i++) {

      view.setUint8(
        offset + i,
        text.charCodeAt(i)
      );
    }
  }


  // ===============================
  // RIFF Header
  // ===============================

  writeString(0, "RIFF");

  view.setUint32(
    4,
    36 + dataSize,
    true
  );

  writeString(8, "WAVE");


  // ===============================
  // fmt Chunk
  // ===============================

  writeString(12, "fmt ");

  view.setUint32(
    16,
    16,
    true
  );

  // PCM format
  view.setUint16(
    20,
    1,
    true
  );

  // Mono channel
  view.setUint16(
    22,
    1,
    true
  );

  // Sample rate
  view.setUint32(
    24,
    sampleRate,
    true
  );

  // Byte rate
  view.setUint32(
    28,
    sampleRate * bytesPerSample,
    true
  );

  // Block align
  view.setUint16(
    32,
    bytesPerSample,
    true
  );

  // 16-bit audio
  view.setUint16(
    34,
    16,
    true
  );


  // ===============================
  // Audio Data Chunk
  // ===============================

  writeString(36, "data");

  view.setUint32(
    40,
    dataSize,
    true
  );


  // ===============================
  // Convert Float32 → 16-bit PCM
  // ===============================

  let position = 44;

  for (let i = 0; i < samples.length; i++) {

    // Keep value between -1 and +1
    const sample =
      Math.max(
        -1,
        Math.min(1, samples[i])
      );

    let pcm;

    if (sample < 0) {

      pcm = sample * 32768;

    } else {

      pcm = sample * 32767;
    }

    view.setInt16(
      position,
      Math.round(pcm),
      true
    );

    position += 2;
  }


  // Return a valid WAV file
  return new Blob(
    [buffer],
    {
      type: "audio/wav"
    }
  );
}


// ===============================
// Stop Recording
// ===============================
async function stopRecording() {

  clearInterval(timer);

  rec.processor.disconnect();

  rec.stream
    .getTracks()
    .forEach(track => track.stop());

  await rec.ctx.close();


  // Create WAV file
  recordedBlob =
    floatToWav(
      rec.data,
      rec.sampleRate
    );


  // Show preview
  $("preview").src =
    URL.createObjectURL(recordedBlob);

  $("preview").hidden = false;


  $("recordBtn").textContent =
    "● Record microphone";

  $("recordBtn")
    .classList
    .remove("recording");

  $("recordState").textContent =
    "Recording ready";

  rec = null;
}


// ===============================
// Record Button
// ===============================
$("recordBtn").onclick = async () => {

  try {

    if (rec) {

      await stopRecording();

    } else {

      await startRecording();
    }

  } catch (e) {

    $("status").textContent =
      "Microphone error: " + e.message;
  }
};


// ===============================
// Audio File Selection
// ===============================
$("audio").onchange = () => {

  $("preview").hidden = true;

  $("recordState").textContent =
    "Reference file selected";

  $("comparisonHint").textContent =
    "Reference file ready. Keep the microphone recording too if you want speaker comparison.";
};


// ===============================
// Context Information
// ===============================
function getContext() {

  return {

    caller_type:
      $("callerType").value,

    call_origin:
      $("origin").value,

    known_contact:
      $("known").value === "true",

    transaction_amount:
      Number($("amount").value || 0),

    previous_fraud_flag:
      $("fraud").value === "true",

    sensitive_action:
      $("sensitive").value === "true"
  };
}


// ===============================
// Layer Progress Bars
// ===============================
function layer(id, val) {

  $(id).style.width =
    val + "%";

  $(id + "V").textContent =
    val + "%";
}


// ===============================
// Analyze Button
// ===============================
$("analyze").onclick = async () => {

  // Microphone recording
  const micFile =
    recordedBlob
      ? new File(
          [recordedBlob],
          "microphone.wav",
          {
            type: "audio/wav"
          }
        )
      : null;


  // Reference audio file
  const referenceFile =
    $("audio").files[0] || null;


  // Need at least one audio input
  if (!micFile && !referenceFile) {

    $("status").textContent =
      "Record or choose an audio file first.";

    return;
  }


  // Create form data
  const fd = new FormData();


  // Main voice
  if (micFile) {

    fd.append(
      "audio",
      micFile
    );
  }


  // Reference voice
  if (referenceFile) {

    fd.append(
      "reference_audio",
      referenceFile
    );
  }


  // Context
  fd.append(
    "context",
    JSON.stringify(
      getContext()
    )
  );


  $("status").textContent =
    "Analyzing voice, context and risk…";

  $("analyze").disabled = true;


  try {

    const response =
      await fetch(
        "/api/analyze",
        {
          method: "POST",
          body: fd
        }
      );


    const d =
      await response.json();


    if (!response.ok) {

      throw new Error(
        d.error ||
        "Analysis failed"
      );
    }


    // ===============================
    // Display Results
    // ===============================

    $("risk").textContent =
      d.risk_score;

    $("voiceRisk").textContent =
      d.voice_risk + "%";

    $("auth").textContent =
      d.authenticity_score + "%";


    $("similarity").textContent =
      d.speaker_similarity === null
        ? "—"
        : d.speaker_similarity + "%";


    $("consistency").textContent =
      d.comparison_status;

    $("level").textContent =
      d.risk_level;

    $("bar").style.width =
      d.risk_score + "%";


    // Alert
    if (d.risk_level === "HIGH") {

      $("alertTitle").textContent =
        "🚨 HIGH RISK CALL";

    } else if (d.risk_level === "MEDIUM") {

      $("alertTitle").textContent =
        "⚠ MEDIUM RISK CALL";

    } else {

      $("alertTitle").textContent =
        "✓ LOW RISK CALL";
    }


    $("rec").textContent =
      d.recommendation;


    // Layer values
    layer(
      "acoustic",
      d.layers.acoustic
    );

    layer(
      "spectral",
      d.layers.spectral
    );

    layer(
      "prosody",
      d.layers.prosody
    );


    $("status").textContent =
      "Analysis complete. " +
      d.comparison_status +
      ". Context adjustment: +" +
      d.context_adjustment +
      " points.";


  } catch (e) {

    $("status").textContent =
      "Error: " + e.message;

  } finally {

    $("analyze").disabled = false;
  }
};