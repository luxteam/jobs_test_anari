import argparse
import platform
import os
import psutil
from subprocess import PIPE, STDOUT, TimeoutExpired


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tool', required=True)
    parser.add_argument('--library', required=True)
    args = parser.parse_args()

    if platform.system() == "Windows":
        import win32gui
        import win32con
        execution_script = "{tool} --library {library}".format(tool=os.path.abspath(args.tool), library=args.library)
        execution_script_path = os.path.abspath("script.bat")
        with open(execution_script_path, "w") as f:
            f.write(execution_script)
    else:
        execution_script = "#!/bin/sh\nexport LD_LIBRARY_PATH={anari_path}; {tool} --library {library}".format(anari_path=os.path.split(args.tool)[0], tool=os.path.abspath(args.tool), library=args.library)
        execution_script_path = os.path.abspath("script.sh")
        with open(execution_script_path, "w") as f:
            f.write(execution_script)
        os.system('chmod +x {}'.format(execution_script_path))

    os.chdir(os.path.split(args.tool)[0])

    p = psutil.Popen(execution_script_path, shell=False, stdout=PIPE, stderr=STDOUT)

    while True:
        try:
            p.wait(timeout=5)
            break
        except (psutil.TimeoutExpired, TimeoutExpired) as e:
            if platform.system() == "Windows":
                crash_window = win32gui.FindWindow(None, "Microsoft Visual C++ Runtime Library")

                if crash_window:
                    message = "Crash window was found"
                    print(message)
                    win32gui.PostMessage(crash_window, win32con.WM_CLOSE, 0, 0)

                    try:
                        for child in reversed(p.children(recursive=True)):
                            child.terminate()
                        p.terminate()
                    except Exception as e1:
                        print("Failed to terminate running process: {}".format(e1))
                    
                    break
