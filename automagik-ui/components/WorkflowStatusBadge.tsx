"use client";

import { Clock, CheckCircle, XCircle, AlertCircle, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface WorkflowStatusBadgeProps {
  status: string;
  className?: string;
  iconOnly?: boolean;
  size?: "sm" | "md" | "lg";
}

export function WorkflowStatusBadge({ 
  status, 
  className, 
  iconOnly = false, 
  size = "md" 
}: WorkflowStatusBadgeProps) {
  const getStatusConfig = (status: string) => {
    switch (status) {
      case "pending":
        return {
          icon: Clock,
          variant: "warning" as const,
          color: "text-yellow-600",
          bgColor: "bg-yellow-50 border-yellow-200"
        };
      case "running":
        return {
          icon: Loader2,
          variant: "info" as const,
          color: "text-blue-600",
          bgColor: "bg-blue-50 border-blue-200",
          animate: "animate-spin"
        };
      case "completed":
        return {
          icon: CheckCircle,
          variant: "success" as const,
          color: "text-green-600",
          bgColor: "bg-green-50 border-green-200"
        };
      case "failed":
        return {
          icon: XCircle,
          variant: "destructive" as const,
          color: "text-red-600",
          bgColor: "bg-red-50 border-red-200"
        };
      default:
        return {
          icon: AlertCircle,
          variant: "secondary" as const,
          color: "text-gray-600",
          bgColor: "bg-gray-50 border-gray-200"
        };
    }
  };

  const getSizeClasses = (size: string) => {
    switch (size) {
      case "sm":
        return iconOnly ? "p-1" : "px-2 py-1 text-xs";
      case "lg":
        return iconOnly ? "p-2" : "px-4 py-2 text-base";
      default:
        return iconOnly ? "p-1.5" : "px-3 py-1.5 text-sm";
    }
  };

  const getIconSize = (size: string) => {
    switch (size) {
      case "sm": return "w-3 h-3";
      case "lg": return "w-6 h-6";
      default: return "w-4 h-4";
    }
  };

  const config = getStatusConfig(status);
  const Icon = config.icon;

  if (iconOnly) {
    return (
      <div
        className={`inline-flex items-center justify-center rounded-full border-2 transition-colors ${config.bgColor} ${getSizeClasses(size)} ${className || ""}`}
        title={status.charAt(0).toUpperCase() + status.slice(1)}
      >
        <Icon className={`${getIconSize(size)} ${config.color} ${config.animate || ""}`} />
      </div>
    );
  }

  return (
    <Badge 
      variant={config.variant}
      className={`inline-flex items-center gap-1.5 ${getSizeClasses(size)} ${className || ""}`}
    >
      <Icon className={`${getIconSize(size)} ${config.animate || ""}`} />
      <span className="capitalize">{status}</span>
    </Badge>
  );
}