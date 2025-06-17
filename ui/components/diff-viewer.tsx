"use client";

import React, { useState, useEffect, useRef } from "react";
import { flushSync } from 'react-dom';
import { EditorView, basicSetup } from 'codemirror';
import { unifiedMergeView, updateOriginalDoc } from '@codemirror/merge';
import { Extension } from '@codemirror/state';
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { githubLight } from "@uiw/codemirror-theme-github";
import { Copy, FileText, ChevronDown, ChevronRight, RotateCcw } from "lucide-react";
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

// Get language extension based on file extension
const getLanguageExtension = (filename: string): Extension | null => {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
        case 'js':
        case 'jsx':
        case 'ts':
        case 'tsx':
            return javascript({ jsx: true });
        case 'py':
            return python();
        default:
            return null;
    }
};

// Unified merge view component for a single file
function FileMergeView({ fileChange }: { fileChange: FileChange }) {
    const [isExpanded, setIsExpanded] = useState(true);
    const [mergedContent, setMergedContent] = useState(fileChange.after);
    const containerRef = useRef<HTMLDivElement>(null);
    const viewRef = useRef<EditorView | null>(null);

    const handleCopyFile = () => {
        navigator.clipboard.writeText(mergedContent);
    };

    useEffect(() => {
        if (!containerRef.current || !isExpanded) return;

        // Clean up previous view if it exists
        if (viewRef.current) {
            viewRef.current.destroy();
            viewRef.current = null;
        }

        // Handle file creation/deletion cases
        const beforeContent = fileChange.before === 'FILE_NOT_EXISTS' ? '' : fileChange.before;
        const afterContent = fileChange.after === 'FILE_DELETED' ? '' : fileChange.after;

        const languageExtension = getLanguageExtension(fileChange.filename);

        const extensions = [
            basicSetup,
            unifiedMergeView({
                original: beforeContent,
                mergeControls: false, // Show accept/reject buttons
                highlightChanges: false,
                gutter: true
            }),
            githubLight, // Apply GitHub light theme
            EditorView.editable.of(false), // Read-only for viewing
            EditorView.theme({
                '.cm-editor': {
                    fontSize: '13px',
                    fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                },
                '.cm-merge-revert': {
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderLeft: '3px solid rgba(239, 68, 68, 0.6)',
                },
                '.cm-merge-accept': {
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    borderLeft: '3px solid rgba(34, 197, 94, 0.6)',
                }
            })
        ];

        // Add language extension if available
        if (languageExtension) {
            extensions.push(languageExtension);
        }

        // Add listener for content changes
        extensions.push(
            EditorView.updateListener.of(update => {
                // Listen for document changes
                if (update.docChanged) {
                    setMergedContent(update.state.doc.toString());
                    return;
                }

                // Listen for merge control actions (accept/revert)
                for (const tr of update.transactions) {
                    for (const effect of tr.effects) {
                        if (effect.is(updateOriginalDoc)) {
                            flushSync(() => {
                                setMergedContent(effect.value.doc.toString());
                            });
                            return;
                        }
                    }
                }
            })
        );

        viewRef.current = new EditorView({
            parent: containerRef.current,
            doc: afterContent,
            extensions,
        });

        return () => {
            if (viewRef.current) {
                viewRef.current.destroy();
                viewRef.current = null;
            }
        };
    }, [isExpanded, fileChange.filename, fileChange.before, fileChange.after]);

    if (!isExpanded) {
        return (
            <div className="border rounded-lg bg-white shadow-sm">
                <div className="px-6 py-4 pb-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 cursor-pointer" onClick={() => setIsExpanded(true)}>
                            <ChevronRight className="w-4 h-4" />
                            <span className="font-mono text-sm">{fileChange.filename}</span>
                            {fileChange.before === 'FILE_NOT_EXISTS' && (
                                <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">NEW</span>
                            )}
                            {fileChange.after === 'FILE_DELETED' && (
                                <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded">DELETED</span>
                            )}
                        </div>
                        <div className="flex items-center gap-1">
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
                        {fileChange.before === 'FILE_NOT_EXISTS' && (
                            <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">NEW</span>
                        )}
                        {fileChange.after === 'FILE_DELETED' && (
                            <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded">DELETED</span>
                        )}
                    </div>
                    <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" onClick={handleCopyFile} title="Copy file content">
                            <Copy className="w-3 h-3" />
                        </Button>
                    </div>
                </div>
            </div>
            <div className="px-6 pb-6 max-h-[500px] overflow-auto">
                <div className="overflow-hidden">
                    <div 
                        ref={containerRef}
                        className="min-h-[200px]"
                        style={{ width: '100%' }}
                    />
                </div>
            </div>
        </div>
    );
}

// Legacy diff viewer for when file changes aren't available
function LegacyDiffViewer({ diff, stats }: { diff: string; stats?: DiffViewerProps['stats'] }) {
    const containerRef = useRef<HTMLDivElement>(null);
    const viewRef = useRef<EditorView | null>(null);

    const handleCopy = () => {
        navigator.clipboard.writeText(diff);
    };

    useEffect(() => {
        if (!containerRef.current) return;

        // Clean up previous view if it exists
        if (viewRef.current) {
            viewRef.current.destroy();
            viewRef.current = null;
        }

        const extensions = [
            basicSetup,
            githubLight,
            EditorView.theme({
                '.cm-editor': {
                    fontSize: '13px',
                    fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                },
            }),
            EditorView.lineWrapping,
            EditorView.editable.of(false),
        ];

        viewRef.current = new EditorView({
            parent: containerRef.current,
            doc: diff,
            extensions
        });

        return () => {
            if (viewRef.current) {
                viewRef.current.destroy();
                viewRef.current = null;
            }
        };
    }, [diff]);

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
                    <div 
                        ref={containerRef}
                        style={{ width: '100%', minHeight: '200px' }}
                    />
                </div>
            </div>
        );
}

export function DiffViewer({ diff, fileChanges, stats, className = "" }: DiffViewerProps) {
    const [expandAll, setExpandAll] = useState(false);

    const handleCopyAll = () => {
        if (fileChanges && fileChanges.length > 0) {
            const allChanges = fileChanges.map(fc => 
                `--- ${fc.filename}\n+++ ${fc.filename}\n${fc.before}\n---\n${fc.after}`
            ).join('\n\n');
            navigator.clipboard.writeText(allChanges);
        } else if (diff) {
            navigator.clipboard.writeText(diff);
        }
    };

    const handleExpandAll = () => {
        setExpandAll(!expandAll);
        // Note: This would need to be implemented with a context or prop drilling
        // to actually control the expand/collapse state of individual files
    };

    // Use unified merge view if file changes are available, otherwise fall back to legacy diff
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
                        <Button 
                            variant="outline" 
                            size="sm" 
                            onClick={handleExpandAll}
                        >
                            {expandAll ? 'Collapse All' : 'Expand All'}
                        </Button>
                        <Button variant="outline" size="sm" onClick={handleCopyAll}>
                            <Copy className="w-3 h-3 mr-1" />
                            Copy All
                        </Button>
                    </div>
                </div>

                {/* File Changes */}
                <div className="space-y-4">
                    {fileChanges.map((fileChange, index) => (
                        <FileMergeView 
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