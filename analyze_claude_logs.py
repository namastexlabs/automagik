#!/usr/bin/env python3
"""
Claude CLI Log Analysis Tool

This script analyzes the actual Claude CLI streaming JSON data to validate
what features are extractable for debug structure development.
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Optional
from datetime import datetime

class ClaudeLogAnalyzer:
    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self.messages = []
        self.turns = []
        self.token_data = []
        self.tool_usage = []
        self.errors = []
        self.mcp_servers = []
        
    def parse_log_file(self):
        """Parse the log file and extract structured data."""
        print(f"📖 Parsing log file: {self.log_path}")
        
        with open(self.log_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                # Remove line number prefix if present (format: "    X→")
                if '→' in line:
                    json_part = line.split('→', 1)[1]
                else:
                    json_part = line
                
                try:
                    data = json.loads(json_part)
                    self._process_message(data, line_num)
                except json.JSONDecodeError as e:
                    print(f"⚠️  JSON decode error on line {line_num}: {e}")
                    continue
    
    def _process_message(self, data: Dict[str, Any], line_num: int):
        """Process individual message from the log."""
        msg_type = data.get('type')
        
        if msg_type == 'system':
            self._process_system_message(data, line_num)
        elif msg_type == 'assistant':
            self._process_assistant_message(data, line_num)
        elif msg_type == 'user':
            self._process_user_message(data, line_num)
        elif msg_type == 'result':
            self._process_result_message(data, line_num)
        
        self.messages.append({
            'line_num': line_num,
            'type': msg_type,
            'data': data
        })
    
    def _process_system_message(self, data: Dict[str, Any], line_num: int):
        """Process system initialization message."""
        if data.get('subtype') == 'init':
            self.mcp_servers = data.get('mcp_servers', [])
            tools = data.get('tools', [])
            print(f"🔧 System init: {len(tools)} tools, {len(self.mcp_servers)} MCP servers")
    
    def _process_assistant_message(self, data: Dict[str, Any], line_num: int):
        """Process assistant message and extract turn data."""
        message = data.get('message', {})
        message_id = message.get('id')
        usage = message.get('usage', {})
        content = message.get('content', [])
        
        # Extract token usage
        if usage:
            token_entry = {
                'line_num': line_num,
                'message_id': message_id,
                'input_tokens': usage.get('input_tokens', 0),
                'output_tokens': usage.get('output_tokens', 0),
                'cache_creation_input_tokens': usage.get('cache_creation_input_tokens', 0),
                'cache_read_input_tokens': usage.get('cache_read_input_tokens', 0),
                'service_tier': usage.get('service_tier')
            }
            self.token_data.append(token_entry)
        
        # Extract tool usage
        for item in content:
            if item.get('type') == 'tool_use':
                tool_entry = {
                    'line_num': line_num,
                    'message_id': message_id,
                    'tool_id': item.get('id'),
                    'tool_name': item.get('name'),
                    'tool_input': item.get('input', {}),
                    'status': 'initiated'
                }
                self.tool_usage.append(tool_entry)
        
        # Track turn
        turn_entry = {
            'line_num': line_num,
            'message_id': message_id,
            'role': 'assistant',
            'model': message.get('model'),
            'content_types': [item.get('type') for item in content],
            'token_usage': usage,
            'tool_calls': len([item for item in content if item.get('type') == 'tool_use'])
        }
        self.turns.append(turn_entry)
    
    def _process_user_message(self, data: Dict[str, Any], line_num: int):
        """Process user message (typically tool results)."""
        message = data.get('message', {})
        content = message.get('content', [])
        
        # Look for tool results
        for item in content:
            if item.get('type') == 'tool_result':
                tool_id = item.get('tool_use_id')
                is_error = item.get('is_error', False)
                result_content = item.get('content', '')
                
                # Update tool usage status
                for tool_entry in self.tool_usage:
                    if tool_entry['tool_id'] == tool_id:
                        tool_entry['status'] = 'error' if is_error else 'success'
                        tool_entry['result'] = result_content
                        if is_error:
                            self.errors.append({
                                'line_num': line_num,
                                'tool_id': tool_id,
                                'error_content': result_content
                            })
                        break
        
        # Track turn
        turn_entry = {
            'line_num': line_num,
            'role': 'user',
            'content_types': [item.get('type') for item in content],
            'tool_results': len([item for item in content if item.get('type') == 'tool_result'])
        }
        self.turns.append(turn_entry)
    
    def _process_result_message(self, data: Dict[str, Any], line_num: int):
        """Process final result message."""
        usage = data.get('usage', {})
        
        # This contains session totals
        session_summary = {
            'line_num': line_num,
            'duration_ms': data.get('duration_ms'),
            'duration_api_ms': data.get('duration_api_ms'),
            'num_turns': data.get('num_turns'),
            'total_cost_usd': data.get('total_cost_usd'),
            'total_usage': usage,
            'is_error': data.get('is_error', False),
            'result': data.get('result')
        }
        self.session_summary = session_summary
    
    def analyze_turn_patterns(self):
        """Analyze turn-by-turn patterns for phase detection."""
        print(f"\n🔍 Turn-by-Turn Analysis:")
        print(f"Total turns: {len(self.turns)}")
        
        phases = []
        current_phase = None
        
        for i, turn in enumerate(self.turns):
            if turn['role'] == 'assistant':
                # Detect phase based on tool usage patterns
                tool_names = []
                for tool in self.tool_usage:
                    if tool['message_id'] == turn['message_id']:
                        tool_names.append(tool['tool_name'])
                
                detected_phase = self._detect_phase(tool_names, turn.get('content_types', []))
                
                if detected_phase != current_phase:
                    if current_phase:
                        phases[-1]['end_turn'] = i - 1
                    phases.append({
                        'phase': detected_phase,
                        'start_turn': i,
                        'end_turn': None,
                        'tools_used': tool_names
                    })
                    current_phase = detected_phase
                
                print(f"  Turn {i+1}: {turn['role']} -> {tool_names} [{detected_phase}]")
        
        if phases and phases[-1]['end_turn'] is None:
            phases[-1]['end_turn'] = len(self.turns) - 1
        
        return phases
    
    def _detect_phase(self, tool_names: List[str], content_types: List[str]) -> str:
        """Detect workflow phase based on tool usage patterns."""
        if 'TodoWrite' in tool_names:
            return 'PLANNING'
        elif any(tool in tool_names for tool in ['Read', 'LS', 'Glob', 'Grep']):
            return 'ANALYSIS'
        elif any(tool in tool_names for tool in ['Write', 'Edit', 'MultiEdit']):
            return 'IMPLEMENTATION'
        elif any(tool in tool_names for tool in ['Bash']):
            return 'EXECUTION'
        elif 'Task' in tool_names:
            return 'DELEGATED_TASK'
        else:
            return 'COMMUNICATION'
    
    def analyze_token_patterns(self):
        """Analyze token usage patterns and cost calculations."""
        print(f"\n💰 Token & Cost Analysis:")
        
        total_input = sum(t['input_tokens'] for t in self.token_data)
        total_output = sum(t['output_tokens'] for t in self.token_data)
        total_cache_creation = sum(t['cache_creation_input_tokens'] for t in self.token_data)
        total_cache_read = sum(t['cache_read_input_tokens'] for t in self.token_data)
        
        print(f"  Total Input Tokens: {total_input:,}")
        print(f"  Total Output Tokens: {total_output:,}")
        print(f"  Total Cache Creation: {total_cache_creation:,}")
        print(f"  Total Cache Read: {total_cache_read:,}")
        
        if hasattr(self, 'session_summary'):
            print(f"  Total Cost: ${self.session_summary.get('total_cost_usd', 0):.6f}")
        
        # Show per-turn breakdown
        print(f"\n  Per-Turn Token Usage:")
        for i, token_data in enumerate(self.token_data[:5]):  # Show first 5
            print(f"    Turn {i+1}: {token_data['input_tokens']} in, {token_data['output_tokens']} out, "
                  f"{token_data['cache_read_input_tokens']} cache read")
        
        if len(self.token_data) > 5:
            print(f"    ... and {len(self.token_data) - 5} more turns")
    
    def analyze_tool_usage(self):
        """Analyze tool usage patterns and success rates."""
        print(f"\n🔨 Tool Usage Analysis:")
        
        tool_stats = defaultdict(lambda: {'count': 0, 'success': 0, 'error': 0})
        
        for tool in self.tool_usage:
            name = tool['tool_name']
            tool_stats[name]['count'] += 1
            if tool['status'] == 'success':
                tool_stats[name]['success'] += 1
            elif tool['status'] == 'error':
                tool_stats[name]['error'] += 1
        
        print(f"  Tools Used: {len(tool_stats)}")
        for tool_name, stats in sorted(tool_stats.items()):
            success_rate = (stats['success'] / stats['count'] * 100) if stats['count'] > 0 else 0
            print(f"    {tool_name}: {stats['count']} calls, {success_rate:.1f}% success")
    
    def analyze_mcp_servers(self):
        """Analyze MCP server information."""
        print(f"\n🌐 MCP Server Analysis:")
        print(f"  Connected Servers: {len(self.mcp_servers)}")
        
        for server in self.mcp_servers:
            print(f"    {server['name']}: {server['status']}")
    
    def analyze_error_patterns(self):
        """Analyze error patterns and recovery."""
        print(f"\n❌ Error Analysis:")
        print(f"  Total Errors: {len(self.errors)}")
        
        for error in self.errors:
            print(f"    Line {error['line_num']}: {error['error_content'][:100]}...")
    
    def extract_concrete_examples(self):
        """Extract concrete examples of each data type."""
        print(f"\n📋 Concrete Data Examples:")
        
        # Message ID example
        if self.turns:
            first_assistant_turn = next((t for t in self.turns if t['role'] == 'assistant'), None)
            if first_assistant_turn:
                print(f"  Message ID Format: {first_assistant_turn['message_id']}")
        
        # Token usage example
        if self.token_data:
            example_tokens = self.token_data[0]
            print(f"  Token Usage Structure: {json.dumps(example_tokens, indent=4)}")
        
        # Tool usage example
        if self.tool_usage:
            example_tool = self.tool_usage[0]
            print(f"  Tool Usage Structure: {json.dumps(example_tool, indent=4)}")
        
        # MCP server example
        if self.mcp_servers:
            print(f"  MCP Server Structure: {json.dumps(self.mcp_servers[0], indent=4)}")
    
    def generate_validation_report(self):
        """Generate a validation report comparing promised vs actual features."""
        print(f"\n🎯 Feature Validation Report:")
        print(f"Log file: {self.log_path}")
        print(f"Total messages: {len(self.messages)}")
        
        # Validate promised features
        features = {
            'Message IDs': bool(any(t.get('message_id') for t in self.turns)),
            'Token Usage Per Turn': bool(self.token_data),
            'Cache Token Tracking': bool(any(t['cache_read_input_tokens'] > 0 for t in self.token_data)),
            'Tool Usage Tracking': bool(self.tool_usage),
            'Tool Success/Failure': bool(any(t['status'] in ['success', 'error'] for t in self.tool_usage)),
            'MCP Server Info': bool(self.mcp_servers),
            'Error Tracking': bool(self.errors),
            'Phase Detection Signals': True,  # We can detect via tool patterns
            'Cost Calculation Data': bool(hasattr(self, 'session_summary') and 'total_cost_usd' in self.session_summary),
            'Duration Tracking': bool(hasattr(self, 'session_summary') and 'duration_ms' in self.session_summary)
        }
        
        print(f"\n✅ Feature Availability:")
        for feature, available in features.items():
            status = "✅ Available" if available else "❌ Missing"
            print(f"  {feature}: {status}")
        
        return features

def main():
    """Main analysis function."""
    log_files = [
        "/home/namastex/workspace/am-agents-labs/logs/raw_stream_test_1749880516.log",
        "/home/namastex/workspace/am-agents-labs/logs/long_workflow_test_1749880570.log"
    ]
    
    print("🚀 Claude CLI Log Analysis")
    print("=" * 50)
    
    all_features = {}
    
    for log_file in log_files:
        if not Path(log_file).exists():
            print(f"❌ Log file not found: {log_file}")
            continue
        
        print(f"\n" + "=" * 80)
        print(f"Analyzing: {Path(log_file).name}")
        print("=" * 80)
        
        analyzer = ClaudeLogAnalyzer(log_file)
        analyzer.parse_log_file()
        
        # Run all analyses
        phases = analyzer.analyze_turn_patterns()
        analyzer.analyze_token_patterns()
        analyzer.analyze_tool_usage()
        analyzer.analyze_mcp_servers()
        analyzer.analyze_error_patterns()
        analyzer.extract_concrete_examples()
        features = analyzer.generate_validation_report()
        
        all_features[Path(log_file).name] = features
        
        print(f"\n📊 Detected Phases: {[p['phase'] for p in phases]}")
    
    # Summary comparison
    print(f"\n" + "=" * 80)
    print("🎯 OVERALL FEATURE VALIDATION SUMMARY")
    print("=" * 80)
    
    if all_features:
        # Get all unique features
        all_unique_features = set()
        for features in all_features.values():
            all_unique_features.update(features.keys())
        
        print(f"\nFeature availability across log files:")
        for feature in sorted(all_unique_features):
            print(f"\n{feature}:")
            for log_name, features in all_features.items():
                status = "✅" if features.get(feature, False) else "❌"
                print(f"  {log_name}: {status}")

if __name__ == "__main__":
    main()