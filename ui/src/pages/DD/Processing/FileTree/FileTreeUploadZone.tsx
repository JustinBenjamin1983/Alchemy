/**
 * FileTreeUploadZone Component
 *
 * Overlay that appears when dragging files from OS.
 * Provides visual feedback for drag-drop upload.
 */
import React from "react";
import { Upload } from "lucide-react";
import { motion } from "framer-motion";

// ============================================================================
// Component
// ============================================================================

export function FileTreeUploadZone() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 z-20 flex items-center justify-center bg-blue-500/10 dark:bg-blue-400/10 border-2 border-dashed border-blue-400 dark:border-blue-500 rounded-lg backdrop-blur-[1px]"
    >
      <div className="text-center p-6">
        <motion.div
          initial={{ scale: 0.9, y: 5 }}
          animate={{ scale: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
        >
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center">
            <Upload className="w-8 h-8 text-blue-600 dark:text-blue-400" />
          </div>
          <p className="text-lg font-semibold text-blue-700 dark:text-blue-300">
            Drop files to upload
          </p>
          <p className="text-sm text-blue-600/70 dark:text-blue-400/70 mt-1">
            Files will be added to the project
          </p>
        </motion.div>
      </div>
    </motion.div>
  );
}

export default FileTreeUploadZone;
