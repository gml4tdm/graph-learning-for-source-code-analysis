import time


def easy_log(step_name: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            print('Starting job:', step_name)
            start = time.time()
            result = func(*args, **kwargs)
            print(f'Finished job: {step_name} (took {time.time() - start:.2f} seconds)')
            return result
        return wrapper
    return decorator

