import cv2
from pyzbar import pyzbar
import streamlit as st

class BarcodeScanner:
    def __init__(self):
        self.camera = None

    def scan_barcode(self):
        """Scan barcode using webcam or manual input"""
        try:
            # Initialize camera
            self.camera = cv2.VideoCapture(0)

            if not self.camera.isOpened():
                st.warning("Could not access webcam. Would you like to enter the barcode manually?")
                manual_barcode = st.text_input("Enter barcode number manually")
                if manual_barcode and st.button("Submit Barcode"):
                    return manual_barcode
                return None

            # Create placeholder for video feed
            frame_placeholder = st.empty()
            stop_button = st.button("Stop Scanner")

            while not stop_button:
                ret, frame = self.camera.read()
                if not ret:
                    st.error("Failed to capture video frame")
                    break

                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Detect barcodes
                barcodes = pyzbar.decode(gray)

                for barcode in barcodes:
                    # Extract barcode data
                    barcode_data = barcode.data.decode("utf-8")

                    # Draw rectangle around barcode
                    (x, y, w, h) = barcode.rect
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                    # Clean up and return data
                    self.camera.release()
                    return barcode_data

                # Display frame
                frame_placeholder.image(frame, channels="BGR")

            return None

        except Exception as e:
            st.error(f"Scanner Error: {str(e)}")
            st.warning("Would you like to enter the barcode manually?")
            manual_barcode = st.text_input("Enter barcode number manually")
            if manual_barcode and st.button("Submit Barcode"):
                return manual_barcode
            return None

        finally:
            if self.camera is not None:
                self.camera.release()