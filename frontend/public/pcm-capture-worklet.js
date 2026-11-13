class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Float32Array(2048);
    this.offset = 0;
  }

  process(inputs, outputs) {
    const input = inputs[0]?.[0];
    const output = outputs[0]?.[0];
    if (output) output.fill(0);
    if (!input) return true;

    let sourceOffset = 0;
    while (sourceOffset < input.length) {
      const count = Math.min(input.length - sourceOffset, this.buffer.length - this.offset);
      this.buffer.set(input.subarray(sourceOffset, sourceOffset + count), this.offset);
      sourceOffset += count;
      this.offset += count;
      if (this.offset === this.buffer.length) {
        const chunk = this.buffer;
        this.buffer = new Float32Array(2048);
        this.offset = 0;
        this.port.postMessage(chunk, [chunk.buffer]);
      }
    }
    return true;
  }
}

registerProcessor("alex-pcm-capture", PcmCaptureProcessor);
