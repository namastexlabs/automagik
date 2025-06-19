"use client";

import React, { useState } from "react";
import { Copy, FileText, ChevronDown, ChevronRight, Plus, Minus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FileChange } from "@/types";

interface DiffViewerProps {
    diff?: string; // Legacy git diff for fallback
    fileChanges?: FileChange[];
    stats?: {
        additions: number;
        deletions: number;
        files: number;
    };
    className?: string;
}

// Simple file diff component (without CodeMirror for now)
function FileDiffView({ fileChange }: { fileChange: FileChange }) {
    const [isExpanded, setIsExpanded] = useState(true);

    const handleCopyFile = () => {
        navigator.clipboard.writeText(fileChange.after || '');
    };

    const renderDiff = () => {
        if (fileChange.diff) {
            return (
                <div className="bg-slate-900 text-slate-100 text-xs font-mono overflow-auto max-h-96">
                    {fileChange.diff.split('\n').map((line, idx) => (
                        <div
                            key={idx}
                            className={`px-4 py-0.5 ${
                                line.startsWith('+') ? 'bg-green-900/30 text-green-300' :
                                line.startsWith('-') ? 'bg-red-900/30 text-red-300' :
                                line.startsWith('@@') ? 'bg-blue-900/30 text-blue-300' :
                                'text-slate-300'
                            }`}
                        >
                            {line}
                        </div>
                    ))}
                </div>
            );
        }

        // Show before/after comparison if no diff
        if (fileChange.before && fileChange.after) {
            return (
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <div className="text-xs text-slate-600 bg-red-50 px-2 py-1 border-b">Before</div>
                        <pre className="bg-slate-50 text-xs overflow-auto max-h-64 p-4">
                            {fileChange.before}
                        </pre>
                    </div>
                    <div>
                        <div className="text-xs text-slate-600 bg-green-50 px-2 py-1 border-b">After</div>
                        <pre className="bg-slate-50 text-xs overflow-auto max-h-64 p-4">
                            {fileChange.after}
                        </pre>
                    </div>
                </div>
            );
        }

        // Show only available content
        const content = fileChange.after || fileChange.before || '';
        return (
            <pre className="bg-slate-50 text-xs overflow-auto max-h-64 p-4">
                {content}
            </pre>
        );
    };

    if (!isExpanded) {
        return (
            <div className="border rounded-lg bg-white shadow-sm">
                <div className="px-6 py-4 pb-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 cursor-pointer" onClick={() => setIsExpanded(true)}>
                            <ChevronRight className="w-4 h-4" />
                            <span className="font-mono text-sm">{fileChange.filename}</span>
                            {fileChange.status === 'added' && (
                                <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">NEW</span>
                            )}
                            {fileChange.status === 'deleted' && (
                                <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded">DELETED</span>
                            )}
                            {fileChange.status === 'modified' && (
                                <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">MODIFIED</span>
                            )}
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="flex items-center gap-1 text-xs">
                                <span className="text-green-600 flex items-center gap-1">
                                    <Plus className="w-3 h-3" />
                                    {fileChange.additions}
                                </span>
                                <span className="text-red-600 flex items-center gap-1">
                                    <Minus className="w-3 h-3" />
                                    {fileChange.deletions}
                                </span>
                            </div>
                            <Button variant="ghost" size="sm" onClick={handleCopyFile}>
                                <Copy className="w-3 h-3" />
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="border rounded-lg bg-white shadow-sm">
            <div className="px-6 py-4 pb-1 border-b">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 cursor-pointer" onClick={() => setIsExpanded(false)}>
                        <ChevronDown className="w-4 h-4" />
                        <span className="font-mono text-sm">{fileChange.filename}</span>
                        {fileChange.status === 'added' && (
                            <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">NEW</span>
                        )}
                        {fileChange.status === 'deleted' && (
                            <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded">DELETED</span>
                        )}
                        {fileChange.status === 'modified' && (
                            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">MODIFIED</span>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1 text-xs">
                            <span className="text-green-600 flex items-center gap-1">
                                <Plus className="w-3 h-3" />
                                {fileChange.additions}
                            </span>
                            <span className="text-red-600 flex items-center gap-1">
                                <Minus className="w-3 h-3" />
                                {fileChange.deletions}
                            </span>
                        </div>
                        <Button variant="ghost" size="sm" onClick={handleCopyFile} title="Copy file content">
                            <Copy className="w-3 h-3" />
                        </Button>
                    </div>
                </div>
            </div>
            <div className="px-6 pb-6">
                {renderDiff()}
            </div>
        </div>
    );
}

// Legacy diff viewer for when file changes aren't available
function LegacyDiffViewer({ diff, stats }: { diff: string; stats?: DiffViewerProps['stats'] }) {
    const handleCopy = () => {
        navigator.clipboard.writeText(diff);
    };

    return (
        <div className="border rounded-lg overflow-hidden">
            {/* Header */}
            <div className="bg-slate-50 border-b px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <span className="text-slate-700 text-sm font-medium">Git Diff</span>
                    {stats && (
                        <div className="flex items-center gap-4 text-sm">
                            <div className="flex items-center gap-1">
                                <FileText className="w-3 h-3 text-slate-500" />
                                <span className="text-slate-600">{stats.files} files</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-green-600 font-mono">+{stats.additions}</span>
                                <span className="text-red-600 font-mono">-{stats.deletions}</span>
                            </div>
                        </div>
                    )}
                </div>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCopy}
                    className="text-slate-600 hover:text-slate-900 hover:bg-slate-200"
                >
                    <Copy className="w-3 h-3" />
                </Button>
            </div>
            
            {/* Diff Content */}
            <div className="max-h-[500px] overflow-auto bg-white">
                <div className="bg-slate-900 text-slate-100 text-xs font-mono">
                    {diff.split('\n').map((line, idx) => (
                        <div
                            key={idx}
                            className={`px-4 py-0.5 ${
                                line.startsWith('+') ? 'bg-green-900/30 text-green-300' :
                                line.startsWith('-') ? 'bg-red-900/30 text-red-300' :
                                line.startsWith('@@') ? 'bg-blue-900/30 text-blue-300' :
                                'text-slate-300'
                            }`}
                        >
                            {line}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export function DiffViewer({ diff, fileChanges, stats, className = "" }: DiffViewerProps) {
    const [expandAll, setExpandAll] = useState(false);

    const handleCopyAll = () => {
        if (fileChanges && fileChanges.length > 0) {
            const allChanges = fileChanges.map(fc => 
                `--- ${fc.filename}\n+++ ${fc.filename}\n${fc.before || ''}\n---\n${fc.after || ''}`
            ).join('\n\n');
            navigator.clipboard.writeText(allChanges);
        } else if (diff) {
            navigator.clipboard.writeText(diff);
        }
    };

    // Use file changes if available, otherwise fall back to legacy diff
    if (fileChanges && fileChanges.length > 0) {
        return (
            <div className={className}>
                {/* Header */}
                <div className="mb-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <h3 className="text-lg font-semibold">File Changes</h3>
                        {stats && (
                            <div className="flex items-center gap-4 text-sm text-slate-600">
                                <div className="flex items-center gap-1">
                                    <FileText className="w-3 h-3" />
                                    <span>{stats.files} files</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-green-600 font-mono">+{stats.additions}</span>
                                    <span className="text-red-600 font-mono">-{stats.deletions}</span>
                                </div>
                            </div>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" onClick={handleCopyAll}>
                            <Copy className="w-3 h-3 mr-1" />
                            Copy All
                        </Button>
                    </div>
                </div>

                {/* File Changes */}
                <div className="space-y-4">
                    {fileChanges.map((fileChange, index) => (
                        <FileDiffView 
                            key={`${fileChange.filename}-${index}`} 
                            fileChange={fileChange}
                        />
                    ))}
                </div>
            </div>
        );
    }

    // Fall back to legacy diff viewer
    if (diff) {
        return (
            <div className={className}>
                <LegacyDiffViewer diff={diff} stats={stats} />
            </div>
        );
    }

    // No diff data available
    return (
        <div className={`text-center py-8 text-slate-500 ${className}`}>
            <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No changes to display</p>
        </div>
    );
}