#!/usr/bin/env python3
import sys
from PyQt5.QtWidgets import QApplication
from src.gui.main_window import MainWindow

def main():
    """Main entry point for the application"""
    app = QApplication(sys.argv)
    app.setApplicationName("Python BitTorrent Client")
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main()) 