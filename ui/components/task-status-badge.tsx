import { Clock, CheckCircle, XCircle, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface TaskStatusBadgeProps {
    status: string;
    className?: string;
    iconOnly?: boolean;
}

export function TaskStatusBadge({ status, className, iconOnly = false }: TaskStatusBadgeProps) {
    const getIconColor = (status: string) => {
        switch (status) {
            case "pending":
                return "text-amber-600";
            case "running":
                return "text-blue-600";
            case "completed":
                return "text-green-600";
            case "failed":
                return "text-red-600";
            default:
                return "text-muted-foreground";
        }
    };

    const getIcon = (status: string) => {
        switch (status) {
            case "pending":
                return <Clock className={cn("w-4 h-4", getIconColor(status))} />;
            case "running":
                return <AlertCircle className={cn("w-4 h-4", getIconColor(status))} />;
            case "completed":
                return <CheckCircle className={cn("w-4 h-4", getIconColor(status))} />;
            case "failed":
                return <XCircle className={cn("w-4 h-4", getIconColor(status))} />;
            default:
                return null;
        }
    };

    if (iconOnly) {
        return (
            <Badge 
                variant="outline" 
                className={cn(
                    "gap-0 p-1.5 rounded-full border-2 transition-colors bg-background text-foreground border-border hover:bg-muted",
                    className
                )}
                title={status}
            >
                {getIcon(status)}
            </Badge>
        );
    } else {
        return (
            <Badge 
                variant="outline" 
                className={cn(
                    "gap-1 transition-colors bg-background text-foreground border-border hover:bg-muted",
                    className
                )}
            >
                {getIcon(status)}
                {status}
            </Badge>
        );
    }
}