FROM python:3.10-slim

WORKDIR /app

# build-essential for packages that compile; libglib2.0-0 and libgomp1 are
# what headless OpenCV and ONNX Runtime need at import time on a slim image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies.
# rapidocr pulls in opencv-python; both it and opencv-python-headless provide
# cv2, so the GUI build is removed and headless reinstalled in the same layer.
# Recipe taken from handwrite-studio, where it runs in production. The
# uninstall is the only step allowed to fail, hence its own subshell, and the
# final step makes a broken OCR install fail the build instead of the
# running service. Constructing the engine also fetches its model files if the
# wheel did not bundle them, so they are baked into the image rather than
# downloaded by the first user who reads a diagram.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && (pip uninstall -y opencv-python 2>/dev/null || true) \
 && pip install --no-cache-dir --force-reinstall --no-deps "opencv-python-headless>=4.9,<5" \
 && python -c "import cv2, onnxruntime; from rapidocr import RapidOCR; RapidOCR(); print('cv2', cv2.__version__, '+ rapidocr ok')"

# Copy source code
COPY src/ /app/src/

# Expose port
EXPOSE 8000

# Set environment variable so Python path finds src
ENV PYTHONPATH=/app/src

# Run uvicorn
CMD ["uvicorn", "citegraph.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
