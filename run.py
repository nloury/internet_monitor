from internet_monitor.monitor_connection import MonitorConnection

def main():
    monitor = MonitorConnection()
    monitor.run_monitor()

if __name__ == '__main__':
    main()