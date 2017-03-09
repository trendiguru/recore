from multiprocessing import Process, Value, cpu_count
import ctypes

# Go here to determine output_ctype:
# https://docs.python.org/2/library/ctypes.html#fundamental-data-types

DEFAULT_NUM_CPU_PERCENTAGE = 0.75


def map(f, inputs, num_processes=None, ouput_ctype=None):
    ouput_ctype = ouput_ctype or ctypes.c_bool
    num_processes = num_processes or int(DEFAULT_NUM_CPU_PERCENTAGE * cpu_count())
    outputs = [Value(ouput_ctype) for i in xrange(num_processes)]
    chunked_inputs = [inputs[i:i + num_processes] for i in xrange(0, len(inputs), num_processes)]
    return_values = []
    for input_chunk in chunked_inputs:
        processes = [Process(target=simple_worker, args=(f, input_chunk[i], outputs[i]))
                     for i in xrange(len(input_chunk))]
        [p.start() for p in processes]
        [p.join() for p in processes]
        [return_values.append(o.value) for o in outputs]
    return return_values


def simple_worker(f, args, output):
    output.value = f(*args)


# ============= TESTS ===============

def run_test():
    import random
    start = time.time()
    image_and_page_urls = [(random.random(), random.random()) for i in xrange(20)]

    outs = map(check_small, image_and_page_urls)

    print "outs: "
    print outs

    print "All set, please come again!"
    print time.time() - start


def check_small(input1, input2):
    print "Will wait then work"
    time.sleep(1)
    return bool(input1 * input2 < 0.25)


if __name__ == '__main__':
    import time

    tstart = time.time()
    run_test()
    print "Run time: " + str(time.time() - tstart)
