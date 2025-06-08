#!/usr/bin/env python3
"""
Keep-alive script to maintain the Flask development server
Monitors the server and restarts it if it stops responding
"""

import subprocess
import time
import requests
import logging
import sys
import os
from threading import Thread

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ServerKeepAlive:
    def __init__(self, port=5000, check_interval=30):
        self.port = port
        self.check_interval = check_interval
        self.server_process = None
        self.running = True
        
    def start_server(self):
        """Start the Flask server"""
        try:
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait(timeout=10)
        except:
            pass
            
        logger.info("Starting Flask server...")
        self.server_process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.getcwd()
        )
        
        # Give server time to start
        time.sleep(10)
        logger.info(f"Flask server started with PID: {self.server_process.pid}")
        
    def check_server_health(self):
        """Check if server is responding"""
        try:
            response = requests.get(f"http://localhost:{self.port}/", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Server health check failed: {e}")
            return False
            
    def monitor_server(self):
        """Monitor server and restart if needed"""
        while self.running:
            if not self.server_process or self.server_process.poll() is not None:
                logger.warning("Server process is not running, restarting...")
                self.start_server()
            elif not self.check_server_health():
                logger.warning("Server not responding, restarting...")
                self.start_server()
            else:
                logger.info("Server is healthy")
                
            time.sleep(self.check_interval)
            
    def stop(self):
        """Stop monitoring and server"""
        self.running = False
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            
    def run(self):
        """Run the keep-alive service"""
        logger.info("Starting Vehicle Scraper API Keep-Alive Service")
        
        # Start initial server
        self.start_server()
        
        # Start monitoring in background
        monitor_thread = Thread(target=self.monitor_server)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down keep-alive service...")
            self.stop()

if __name__ == "__main__":
    keep_alive = ServerKeepAlive()
    keep_alive.run()