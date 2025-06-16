"use client";

import { Toaster as Sonner } from "sonner";

interface ToasterProps {
  position?: "top-left" | "top-right" | "bottom-left" | "bottom-right" | "top-center" | "bottom-center";
  expand?: boolean;
  richColors?: boolean;
  closeButton?: boolean;
}

export function Toaster({ position = "top-right", expand = false, richColors = true, closeButton = true }: ToasterProps) {
  return (
    <Sonner
      position={position}
      expand={expand}
      richColors={richColors}
      closeButton={closeButton}
      toastOptions={{
        style: {
          background: 'white',
          color: 'rgb(31, 41, 55)',
          border: '1px solid rgb(229, 231, 235)',
          fontSize: '14px',
        },
      }}
    />
  );
}