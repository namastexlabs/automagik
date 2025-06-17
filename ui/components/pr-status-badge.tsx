import { GitPullRequest, ExternalLink, GitMerge } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface PRStatusBadgeProps {
    prUrl?: string | null;
    prNumber?: number | null;
    prBranch?: string | null;
    prStatus?: "open" | "merged" | "closed";
    variant?: "badge" | "button";
    size?: "sm" | "default";
    className?: string;
}

export function PRStatusBadge({ 
    prUrl, 
    prNumber, 
    prBranch, 
    prStatus = "open",
    variant = "badge",
    size = "sm",
    className 
}: PRStatusBadgeProps) {
    if (!prUrl || !prNumber) {
        return null;
    }

    const handleClick = () => {
        if (prUrl) {
            window.open(prUrl, '_blank', 'noopener,noreferrer');
        }
    };

    const getStatusConfig = (status: string) => {
        switch (status) {
            case "merged":
                return {
                    icon: <GitMerge className="w-4 h-4 text-purple-600" />,
                    text: "Merged",
                    className: "bg-background text-foreground border-border hover:bg-muted"
                };
            case "open":
                return {
                    icon: <GitPullRequest className="w-4 h-4 text-green-600" />,
                    text: "Open",
                    className: "bg-background text-foreground border-border hover:bg-muted"
                };
            case "closed":
                return {
                    icon: <GitPullRequest className="w-4 h-4 text-red-600" />,
                    text: "Closed",
                    className: "bg-background text-foreground border-border hover:bg-muted"
                };
            default:
                return {
                    icon: <GitPullRequest className="w-4 h-4 text-blue-600" />,
                    text: "PR",
                    className: "bg-background text-foreground border-border hover:bg-muted"
                };
        }
    };

    const config = getStatusConfig(prStatus);

    if (variant === "button") {
        return (
            <Button 
                onClick={handleClick}
                variant="outline" 
                size={size}
                className={cn("gap-2 transition-colors", config.className, className)}
            >
                {config.icon}
                <span>#{prNumber}</span>
                <ExternalLink className={cn(size === "sm" ? "w-3 h-3" : "w-4 h-4")} />
            </Button>
        );
    }

    return (
        <Badge 
            onClick={handleClick}
            variant="outline" 
            className={cn(
                "gap-1 cursor-pointer transition-all hover:shadow-sm",
                config.className,
                className
            )}
        >
            {config.icon}
            <span>#{prNumber}</span>
            <ExternalLink className="w-3 h-3" />
        </Badge>
    );
}