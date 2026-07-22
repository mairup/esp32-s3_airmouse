import math

/// Low-latency adaptive first-order low-pass filter (1 Euro Filter).
///
/// Designed to suppress high-frequency hand jitter at low movement speeds using
/// `min-cutoff`, while dynamically raising the cutoff frequency during rapid
/// movements (scaled by `beta`) to eliminate response lag.
class OneEuroFilter:
  min-cutoff /float
  beta /float
  d-cutoff /float

  x-prev_ /float? := null
  dx-prev_ /float := 0.0

  /// Creates a 1 Euro Filter with configurable parameters.
  ///
  /// `min-cutoff` (Hz) sets the minimum cutoff frequency for low-speed jitter suppression.
  /// `beta` is the speed coefficient scaling cutoff frequency during fast motion.
  /// `d-cutoff` (Hz) sets the cutoff frequency used to filter the derivative signal.
  constructor --.min-cutoff/float=1.0 --.beta/float=0.005 --.d-cutoff/float=1.0:

  /// Filters a single sample `val` given the elapsed time `delta-seconds`.
  ///
  /// Evaluates derivative filtering, adaptive cutoff frequency calculation, and
  /// exponential smoothing. Returns the filtered value.
  filter --val/float --delta-seconds/float -> float:
    if delta-seconds <= 0.0:
      return val

    if not x-prev_:
      x-prev_ = val
      dx-prev_ = 0.0
      return val

    // 1. Calculate raw rate of change (derivative)
    dx-raw := (val - x-prev_) / delta-seconds

    // 2. Filter derivative using fixed d-cutoff
    alpha-d := compute-alpha_ --cutoff=d-cutoff --delta-seconds=delta-seconds
    dx-filtered := apply-low-pass_ --current=dx-raw --prev=dx-prev_ --alpha=alpha-d
    dx-prev_ = dx-filtered

    // 3. Calculate adaptive cutoff frequency based on speed
    cutoff := min-cutoff + beta * dx-filtered.abs

    // 4. Filter signal value using adaptive cutoff
    alpha := compute-alpha_ --cutoff=cutoff --delta-seconds=delta-seconds
    x-filtered := apply-low-pass_ --current=val --prev=x-prev_ --alpha=alpha
    x-prev_ = x-filtered

    return x-filtered

  /// Resets the internal state of the filter.
  ///
  /// Clears previous sample history and derivative values.
  reset -> none:
    x-prev_ = null
    dx-prev_ = 0.0

  /// Computes the smoothing factor alpha for a given cutoff frequency and delta time.
  compute-alpha_ --cutoff/float --delta-seconds/float -> float:
    tau := 1.0 / (2.0 * math.PI * cutoff)
    return 1.0 / (1.0 + (tau / delta-seconds))

  /// Applies exponential moving average low-pass smoothing.
  apply-low-pass_ --current/float --prev/float --alpha/float -> float:
    return alpha * current + (1.0 - alpha) * prev
