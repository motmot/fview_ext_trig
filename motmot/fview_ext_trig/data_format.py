from tables import IsDescription, UInt16Col, UInt64Col, FloatCol, Float32Col
class AnalogInputWordstreamDescription(IsDescription):
    word = UInt16Col()

class TimeDataDescription(IsDescription):
    timestamp = FloatCol(pos=0)
    framestamp = FloatCol(pos=1)
