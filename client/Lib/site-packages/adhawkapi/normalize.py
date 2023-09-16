'''normalization functions'''


def linearnorm(val, inputrange=(0, 1023), outputrange=(0, 4095)):
    '''
    Linearly interpolates (map) a number in the input range to a number
    in the output range. Treats all operations as float as to not compromise on accuracy
    type casting is left to the caller.

    Args:
        val: a number that falls within the input range
        inputrange: a sorted (ascending) list-like object of length 2
                    that defines the input range: inputmin = inputrange[0]
                    and inputmax = inputrange[1]
        outputrange: a sorted (ascending) list-like object of length 2
                     that defines the input range: inputmin = inputrange[0]
                     and inputmax = inputrange[1]
    '''

    inputmin = float(inputrange[0])
    inputmax = float(inputrange[-1])
    outputmin = float(outputrange[0])
    outputmax = float(outputrange[-1])
    val = float(val)

    # sanity checks
    if len(inputrange) != 2 or len(outputrange) != 2:
        raise TypeError('Range type is not the right length. Must be 2 (min, max)')

    if inputmin > inputmax or outputmin > outputmax:
        raise TypeError('Range is not sorted. Must be (min, max)')

    if val < inputmin or val > inputmax:
        raise TypeError('Value provided does not fall within the input range specified')

    # handle extremeties by direct assignment
    if val == inputmax:
        return outputmax
    if val == inputmin:
        return outputmin

    # linear val(x) = m*x + b interploation from inputrange --> outputrange
    # NOTE: the " + 1" should not be there, we've had to put this here because
    # somehwere jitterscanner app does not map as expecte (4095/1023)
    gain = (outputmax - outputmin + 1) / (inputmax - inputmin + 1)
    val = max(min(val, inputmax), inputmin) - inputmin
    offset = outputmin
    val = gain * val + offset

    return val


def linearnormabs(val, inputabsmax=1023, outputabsmax=4095):
    '''
    Applies linearnorm in the following (absolute) range symmetrical about 0:
    inputrange = (-inputabsmax, inputabsmax) and outputrange = (-outputabsmax, outputabsmax).

    Args:
        val: a number that falls within (-inputabsmax, inputabsmax)
        inputabsmax: input set amplitude about 0, must be positive
        outputabsmax: output set amplitude about 0, must be positivr
    '''

    if inputabsmax < 0 or outputabsmax < 0:
        raise TypeError

    if val >= 0:
        inputrange = (0, inputabsmax)
        outputrange = (0, outputabsmax)
    else:
        inputrange = (-inputabsmax, 0)
        outputrange = (-outputabsmax, 0)

    return linearnorm(val, inputrange, outputrange)


def normalize(val, inputrange, outputrange, clip=True):
    '''Normalize a value from one range to another'''
    inputmin = float(inputrange[0])
    inputmax = float(inputrange[-1])
    outputmin = float(outputrange[0])
    outputmax = float(outputrange[-1])
    val = float(val)

    # sanity checks
    if len(inputrange) != 2 or len(outputrange) != 2:
        raise TypeError('Range type is not the right length. Must be 2 (min, max)')

    if inputmin > inputmax or outputmin > outputmax:
        raise TypeError('Range is not sorted. Must be (min, max)')

    if not clip and (val < inputmin or val > inputmax):
        raise TypeError('Value provided does not fall within the input range specified')

    # handle extremeties by direct assignment
    if val >= inputmax:
        return outputmax
    if val <= inputmin:
        return outputmin

    gain = (outputmax - outputmin) / (inputmax - inputmin)
    val = max(min(val, inputmax), inputmin) - inputmin
    offset = outputmin
    val = gain * val + offset

    return val
