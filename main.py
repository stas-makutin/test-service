import argparse
import platform
import application

argParser = argparse.ArgumentParser(description='Test Python Service.')
argParser.add_argument('-i', '--install', action='store_true', help='Install as service')
argParser.add_argument('-u', '--uninstall', action='store_true', help='Uninstall service')
argParser.add_argument('-s', '--start', action='store_true', help='Start service')
argParser.add_argument('--stop', action='store_true', help='Stop service')
argParser.add_argument('-r', '--restart', action='store_true', help='Restart service')
argParser.add_argument('--status', action='store_true', help='Print service status')
argParser.add_argument('--console', action='store_true', help='Run as terminal application')

args = argParser.parse_args();
isWindows = platform.system() == "Windows"

if args.console:
    import console
    console.run()    
else:
    if isWindows:
        import windowsvc
        service = windowsvc.WindowsService
    else:
        import nixsvc
        service = nixsvc.NixService

    printUsage = True
    
    if args.install:
        printUsage = False
        service.Install()
    elif args.uninstall:
        printUsage = False
        service.Uninstall()

    if args.stop or args.restart:
        printUsage = False
        service.Stop()
    if args.start or args.restart:
        printUsage = False
        service.Start()
    if args.status:
        printUsage = False
        service.Status()

    if printUsage:
        argParser.print_help()