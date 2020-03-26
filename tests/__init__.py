from .test_custom_network_dir import test, cleanup

exit_code = 0
try:
    test()
except:
    exit_code = 1
finally:
    cleanup()

exit(exit_code)
