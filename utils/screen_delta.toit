/// Represents calculated 2D screen coordinate movement deltas.
class ScreenDelta:
  delta-x /float
  delta-y /float

  /// Creates a ScreenDelta instance with horizontal (`delta-x`) and vertical (`delta-y`) movement values.
  constructor --.delta-x/float --.delta-y/float:
