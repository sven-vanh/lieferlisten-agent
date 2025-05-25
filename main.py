# Main Execution
# This script provides a command-line interface for transferring annotations
# between PDF documents using the AnnotationTransferAgent class.
# Created by: Sven van Helten
# Version: 1.0
# Date Edited: 25.05.2025

# Import dependencies
from ata import AnnotationTransferAgent
import logging
import sys
import argparse


# Define main execution function
def main():
    """Main function for command-line usage."""
    # Define the command-line argument parser 
    parser = argparse.ArgumentParser(description="Transfer annotations between PDF documents")
    parser.add_argument("source_pdf", help="Path to source PDF with annotations")
    parser.add_argument("target_pdf", help="Path to target PDF")
    parser.add_argument("output_pdf", help="Path for output PDF")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")
    
    # Parse the command-line arguments passed to the script
    args = parser.parse_args()
    
    # Convert log level string to logging constant
    log_level = getattr(logging, args.log_level.upper())
    
    # Create and run the transfer agent
    agent = AnnotationTransferAgent(log_level=log_level)
    success = agent.transfer_annotations(
        args.source_pdf, args.target_pdf, args.output_pdf
    )
    
    # Check if the transfer was successful and print appropriate message
    if success:
        print("Annotation transfer completed successfully!")
        sys.exit(0)
    # If transfer failed, print error message and exit with non-zero status
    else:
        print("Annotation transfer failed. Check logs for details.")
        sys.exit(1)


# Run the main function if this script is executed directly
if __name__ == "__main__":
    main()
