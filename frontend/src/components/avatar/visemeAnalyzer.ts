/**
 * Formant Viseme Analyzer (TASK-P4-05 / CAT-02)
 *
 * Maps audio frequency formants and spoken text characters into 5 canonical
 * facial visemes:
 *  1. 'sil' (Neutral / Closed)
 *  2. 'aa'  (Open Vowel: a, ah)
 *  3. 'oo'  (Rounded Lips: o, u, w)
 *  4. 'ee'  (Wide Smile: e, i)
 *  5. 'ch'  (Jaw Drop / Fricative: s, sh, ch)
 */

export interface VisemeShape {
  open: number; // 0..1 jaw opening
  wide: number; // -1 (rounded/pursed) .. +1 (spread/wide)
  closure: number; // 0..1 (forces lips shut on m, b, p)
  name: "sil" | "aa" | "oo" | "ee" | "ch";
}

export const CANONICAL_VISEMES: Record<string, VisemeShape> = {
  sil: { open: 0.0, wide: 0.0, closure: 0.0, name: "sil" },
  aa: { open: 0.95, wide: -0.05, closure: 0.0, name: "aa" },
  oo: { open: 0.52, wide: -0.75, closure: 0.0, name: "oo" },
  ee: { open: 0.40, wide: 0.70, closure: 0.0, name: "ee" },
  ch: { open: 0.22, wide: 0.35, closure: 0.0, name: "ch" },
};

// Text character to viseme mapping (multilingual reduction)
const LETTER_VISEMES: Record<string, keyof typeof CANONICAL_VISEMES> = {
  a: "aa",
  e: "ee",
  i: "ee",
  y: "ee",
  o: "oo",
  u: "oo",
  w: "oo",
  s: "ch",
  z: "ch",
  c: "ch",
  j: "ch",
  x: "ch",
  t: "ch",
  d: "ch",
  k: "ch",
  g: "ch",
  b: "sil",
  p: "sil",
  m: "sil",
  f: "ch",
  v: "ch",
  l: "ee",
  r: "oo",
};

export class VisemeAnalyzer {
  private currentOpen = 0.0;
  private currentWide = 0.0;
  private currentClosure = 0.0;
  private currentViseme: "sil" | "aa" | "oo" | "ee" | "ch" = "sil";

  /**
   * Resolve a text character or token to its canonical viseme shape.
   */
  public analyzeTextChar(char: string): VisemeShape {
    const clean = char.toLowerCase().trim();
    if (!clean) return CANONICAL_VISEMES.sil;
    const baseChar = clean[0].normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    const visemeKey = LETTER_VISEMES[baseChar] || "ch";
    return CANONICAL_VISEMES[visemeKey];
  }

  /**
   * Analyze audio frequency spectrum (FFT bands from 300 Hz to 3000 Hz)
   * to determine mouth openness and lip spread.
   *
   * Formant ranges (assuming sample rate 16kHz - 48kHz and 512-point FFT):
   * - F1 (300-800 Hz): Openness (Vowel height)
   * - F2 (900-2400 Hz): Lip spread (front/spread vowel) vs rounding (back vowel)
   * - High (2400-3600 Hz): Fricative / teeth
   */
  public analyzeFormants(
    freqData: Uint8Array | Float32Array,
    sampleRate = 44100,
  ): VisemeShape {
    const binCount = freqData.length;
    const binWidth = (sampleRate / 2) / binCount;
    const isUint8 = freqData instanceof Uint8Array;

    let f1Sum = 0;
    let f1Count = 0;
    let f2LowSum = 0;
    let f2LowCount = 0;
    let f2HighSum = 0;
    let f2HighCount = 0;
    let fHighSum = 0;
    let fHighCount = 0;

    for (let i = 0; i < binCount; i++) {
      const freq = i * binWidth;
      const mag = isUint8 ? freqData[i] / 255.0 : Math.max(0, freqData[i]);

      if (freq >= 300 && freq < 850) {
        f1Sum += mag;
        f1Count++;
      } else if (freq >= 850 && freq < 1600) {
        f2LowSum += mag;
        f2LowCount++;
      } else if (freq >= 1600 && freq < 2800) {
        f2HighSum += mag;
        f2HighCount++;
      } else if (freq >= 2800 && freq < 4500) {
        fHighSum += mag;
        fHighCount++;
      }
    }

    const f1Avg = f1Count > 0 ? f1Sum / f1Count : 0;
    const f2LowAvg = f2LowCount > 0 ? f2LowSum / f2LowCount : 0;
    const f2HighAvg = f2HighCount > 0 ? f2HighSum / f2HighCount : 0;
    const fHighAvg = fHighCount > 0 ? fHighSum / fHighCount : 0;

    const totalEnergy = f1Avg + f2LowAvg + f2HighAvg + fHighAvg;
    if (totalEnergy < 0.04) {
      return CANONICAL_VISEMES.sil;
    }

    // F1 drives jaw openness
    const open = Math.min(1.0, f1Avg * 2.3);

    let wide = 0.0;
    let viseme: "sil" | "aa" | "oo" | "ee" | "ch" = "aa";

    if (fHighAvg > f1Avg * 1.1 && fHighAvg > 0.15) {
      // High frequency sibilance/fricatives (s, z, ch)
      wide = 0.35;
      viseme = "ch";
    } else if (f2HighAvg > f2LowAvg * 1.25) {
      // High F2 -> front vowel (ee / ih)
      wide = Math.min(0.85, (f2HighAvg - f2LowAvg) * 2.2);
      viseme = "ee";
    } else if (f2LowAvg > f2HighAvg * 1.15) {
      // Low F2 -> back vowel (oo / oh / uu)
      wide = -Math.min(0.85, (f2LowAvg - f2HighAvg) * 2.2);
      viseme = "oo";
    } else if (open > 0.35) {
      wide = -0.05;
      viseme = "aa";
    } else {
      wide = 0.25;
      viseme = "ch";
    }

    return {
      open,
      wide,
      closure: 0.0,
      name: viseme,
    };
  }

  /**
   * Advance one simulation tick, smoothly interpolating to target shape.
   */
  public step(dt: number, target: VisemeShape): VisemeShape {
    // Time constants (seconds)
    const tauOpen = target.open > this.currentOpen ? 0.022 : 0.045;
    const tauWide = 0.035;

    const rateOpen = 1.0 - Math.exp(-dt / tauOpen);
    const rateWide = 1.0 - Math.exp(-dt / tauWide);

    this.currentOpen += (target.open - this.currentOpen) * rateOpen;
    this.currentWide += (target.wide - this.currentWide) * rateWide;
    this.currentClosure = target.closure;
    this.currentViseme = target.name;

    return {
      open: this.currentOpen,
      wide: this.currentWide,
      closure: this.currentClosure,
      name: this.currentViseme,
    };
  }

  public getShape(): VisemeShape {
    return {
      open: this.currentOpen,
      wide: this.currentWide,
      closure: this.currentClosure,
      name: this.currentViseme,
    };
  }
}
