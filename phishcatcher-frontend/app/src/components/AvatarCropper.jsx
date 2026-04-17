import { useState, useRef, useCallback } from 'react';
import ReactCrop from 'react-image-crop';
import 'react-image-crop/dist/ReactCrop.css';

const AvatarCropper = ({
  imageSrc,
  onCrop,
  onCancel,
}) => {
  const [crop, setCrop] = useState();
  const [completedCrop, setCompletedCrop] = useState();
  const imgRef = useRef(null);

  const onImageLoad = useCallback((e) => {
    const { naturalWidth, naturalHeight } = e.currentTarget;
    const size = Math.min(naturalWidth, naturalHeight);
    
    setCrop({
      unit: 'px',
      width: size,
      height: size,
      x: (naturalWidth - size) / 2,
      y: (naturalHeight - size) / 2,
    });
  }, []);

  const handleCropComplete = useCallback((c) => {
    setCompletedCrop(c);
  }, []);

  const getCroppedImage = useCallback(() => {
    if (!imgRef.current || !completedCrop) return null;

    const image = imgRef.current;
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    if (!ctx) return null;

    // Normalize crop coordinates to actual pixel values
    const scaleX = image.naturalWidth / image.width;
    const scaleY = image.naturalHeight / image.height;

    let cropX, cropY, cropWidth, cropHeight;

    if (completedCrop.unit === '%') {
      cropX = (completedCrop.x / 100) * image.naturalWidth;
      cropY = (completedCrop.y / 100) * image.naturalHeight;
      cropWidth = (completedCrop.width / 100) * image.naturalWidth;
      cropHeight = (completedCrop.height / 100) * image.naturalHeight;
    } else {
      cropX = completedCrop.x * scaleX;
      cropY = completedCrop.y * scaleY;
      cropWidth = completedCrop.width * scaleX;
      cropHeight = completedCrop.height * scaleY;
    }

    // Create square crop from center
    const size = Math.min(cropWidth, cropHeight);
    const centerX = cropX + cropWidth / 2;
    const centerY = cropY + cropHeight / 2;
    const finalX = centerX - size / 2;
    const finalY = centerY - size / 2;

    canvas.width = 256;
    canvas.height = 256;

    ctx.drawImage(
      image,
      finalX, finalY, size, size,  // Source rect
      0, 0, 256, 256               // Dest rect
    );

    return new Promise((resolve) => {
      canvas.toBlob(
        (blob) => {
          resolve(blob);
        },
        'image/png',
        1.0
      );
    });
  }, [completedCrop]);

  const handleUpload = async () => {
    const croppedBlob = await getCroppedImage();
    if (croppedBlob) {
      croppedBlob.name = 'avatar.png';
      onCrop(croppedBlob);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Crop Your Avatar
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Move and resize to select your avatar area
          </p>
        </div>

        <div className="p-6 flex flex-col items-center">
          <div className="relative w-64 h-64 overflow-hidden rounded-lg border-4 border-gray-200 dark:border-gray-600 bg-black">
            <ReactCrop
              crop={crop}
              onChange={(c) => setCrop(c)}
              onComplete={handleCropComplete}
              aspect={1}
            >
              <img
                ref={imgRef}
                src={imageSrc}
                alt="Upload preview"
                onLoad={onImageLoad}
                className="max-w-none"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            </ReactCrop>
          </div>

          <div className="flex gap-3 w-full mt-4">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleUpload}
              disabled={!completedCrop}
              className="flex-1 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Upload
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AvatarCropper;
