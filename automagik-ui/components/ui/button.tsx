"use client";

import * as React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info";
}

const buttonVariants = {
  default: "border-transparent bg-gray-900 text-white hover:bg-gray-800",
  secondary: "border-transparent bg-gray-100 text-gray-900 hover:bg-gray-200",
  destructive: "border-transparent bg-red-500 text-white hover:bg-red-600",
  outline: "text-gray-900 border-gray-300",
  success: "border-transparent bg-green-100 text-green-800 hover:bg-green-200",
  warning: "border-transparent bg-yellow-100 text-yellow-800 hover:bg-yellow-200",
  info: "border-transparent bg-blue-100 text-blue-800 hover:bg-blue-200",
};

function Button({ className, variant = "default", ...props }: ButtonProps) {
  return (
    <button 
      className={`inline-flex items-center rounded-md border px-4 py-2 text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300 focus:ring-offset-2 ${buttonVariants[variant]} ${className || ""}`} 
      {...props} 
    />
  );
}

export { Button };