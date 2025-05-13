#!/usr/bin/env python3
import sys
import os # Import os for path operations
from PyQt5.QtWidgets import QApplication
from src.gui.main_window import MainWindow

STYLE_SHEET_PATH = os.path.join(os.path.dirname(__file__), "src", "gui", "style.qss") # More robust path

def main():
    """Main entry point for the application"""
    app = QApplication(sys.argv)
    app.setApplicationName("Python BitTorrent Client")
    app.setStyle("Fusion")
    
    # Load and apply stylesheet
    qss_file = os.path.abspath(STYLE_SHEET_PATH)
    if os.path.exists(qss_file):
        try:
            with open(qss_file, "r") as f:
                app.setStyleSheet(f.read())
            print(f"Stylesheet loaded from {qss_file}") # For confirmation
        except Exception as e:
            print(f"Error loading stylesheet {qss_file}: {e}", file=sys.stderr)
    else:
        print(f"Warning: Stylesheet not found at {qss_file}", file=sys.stderr)
    
    window = MainWindow()
    window.show()
    
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main()) 