import sys
import xdart


if __name__ == '__main__':
    while True:
        command = input(
            "Choose experiment:\n" +
            "a) Two Theta Scan\n" +
            "q) Quit\n"
        )
        if command == 'q':
            sys.exit()
        elif command == 'a':
            xdart.experiments.ttheta_scan.main()
        else:
            print('***Invalid command***\n')

