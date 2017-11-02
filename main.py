import argparse
import platform
import application

isWindows = platform.system() == "Windows"

argParser = argparse.ArgumentParser(description='Test Python Service.')
argParser.add_argument('-i', '--install', action='store_true', help='Install as service')
argParser.add_argument('-u', '--uninstall', action='store_true', help='Uninstall service')
argParser.add_argument('-s', '--start', action='store_true', help='Start service')
argParser.add_argument('--stop', action='store_true', help='Stop service')
argParser.add_argument('-r', '--restart', action='store_true', help='Restart service')
argParser.add_argument('--console', action='store_true', help='Run as terminal application')
if not isWindows:
    argParser.add_argument('--daemonize', action='store_true', help='Run as daemon')
argParser.add_argument('-p', '--port', type=int, default=8888, help='HTTP server port, default %(default)d.')

args = argParser.parse_args();

if args.console:
    import console
    
    app = application.Application(args.port)
    console.run(app)    
else:
    daemonize = False
    if isWindows:
        import windowsvc
        service = windowsvc.WindowsService
    else:
        import nixsvc
        service = nixsvc.NixService()
        daemonize = args.daemonize

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

    if daemonize and not isWindows:
        service.Run()
    elif printUsage:
        argParser.print_help()