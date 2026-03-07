#!/usr/bin/env python3
"""
VersaAI CLI - Interactive coding assistant with full VersaAI capabilities

Features:
- Interactive chat mode
- Code generation, explanation, review, debugging
- Memory and context management
- Syntax highlighting
- Beautiful terminal UI
"""

import os
import sys
import argparse
import readline  # For command history
from typing import Optional
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Install 'rich' for better UI: pip install rich")

from versaai.models.code_model import CodeModel, CodeContext, CodeTaskType


class VersaAICLI:
    """Interactive CLI for VersaAI Code Assistant"""
    
    def __init__(
        self, 
        model_id: str = "code-assistant-v1",
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        multi_model_manager: Optional[object] = None,
        **llm_kwargs
    ):
        self.console = Console() if RICH_AVAILABLE else None
        self.multi_model_manager = multi_model_manager
        
        # If multi-model mode, don't initialize model yet
        if multi_model_manager:
            self.model = None
            self.multi_model_mode = True
        else:
            self.model = CodeModel(
                model_id=model_id,
                enable_memory=True,
                enable_rag=True,
                llm_provider=llm_provider,
                llm_model=llm_model,
                **llm_kwargs
            )
            self.multi_model_mode = False
        
        self.current_language = "python"
        self.current_file = None
        self.running = True
        
        self._setup_readline()
        self._print_welcome()
        
        # Show LLM status
        if multi_model_manager:
            self._print_info("🎯 Multi-model mode enabled - best model will be selected for each task")
        elif llm_provider and llm_model:
            self._print_info(f"Using {llm_provider} LLM: {llm_model}")
        else:
            self._print_info("Running in placeholder mode (no LLM). Use --provider and --model to enable real code generation.")
    
    def _setup_readline(self):
        """Setup readline for command history"""
        histfile = Path.home() / ".versaai_history"
        try:
            readline.read_history_file(histfile)
            readline.set_history_length(1000)
        except FileNotFoundError:
            pass
        
        import atexit
        atexit.register(readline.write_history_file, histfile)
    
    def _print_welcome(self):
        """Print welcome message"""
        if self.console:
            self.console.print(Panel.fit(
                "[bold cyan]VersaAI Code Assistant[/bold cyan]\n"
                "Your intelligent coding companion\n\n"
                "Type [yellow]help[/yellow] for commands, [yellow]quit[/yellow] to exit",
                border_style="cyan"
            ))
        else:
            print("\n" + "="*70)
            print("  VersaAI Code Assistant")
            print("  Your intelligent coding companion")
            print("\n  Type 'help' for commands, 'quit' to exit")
            print("="*70 + "\n")
    
    def run(self):
        """Main interactive loop"""
        while self.running:
            try:
                # Get user input
                if self.console:
                    user_input = Prompt.ask(
                        f"[bold green]VersaAI[/bold green] [{self.current_language}]"
                    )
                else:
                    user_input = input(f"VersaAI [{self.current_language}]> ").strip()
                
                if not user_input:
                    continue
                
                # Process command or query
                self._process_input(user_input)
                
            except KeyboardInterrupt:
                print("\n")
                if self._confirm("Exit VersaAI?"):
                    self.running = False
            except EOFError:
                print("\n")
                self.running = False
            except Exception as e:
                self._print_error(f"Error: {e}")
        
        self._print_goodbye()
    
    def _process_input(self, user_input: str):
        """Process user input (command or query)"""
        # Check for commands
        if user_input.startswith('/'):
            self._handle_command(user_input[1:])
        else:
            # Regular query - use code model
            self._handle_query(user_input)
    
    def _handle_command(self, command: str):
        """Handle CLI commands"""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        commands = {
            'help': self._cmd_help,
            'lang': self._cmd_set_language,
            'language': self._cmd_set_language,
            'generate': self._cmd_generate,
            'gen': self._cmd_generate,
            'explain': self._cmd_explain,
            'review': self._cmd_review,
            'debug': self._cmd_debug,
            'refactor': self._cmd_refactor,
            'test': self._cmd_test,
            'history': self._cmd_history,
            'clear': self._cmd_clear,
            'load': self._cmd_load_file,
            'save': self._cmd_save,
            'quit': self._cmd_quit,
            'exit': self._cmd_quit,
        }
        
        if cmd in commands:
            commands[cmd](args)
        else:
            self._print_error(f"Unknown command: /{cmd}. Type /help for commands.")
    
    def _handle_query(self, query: str):
        """Handle natural language query"""
        # Detect task type from query
        task_type = self._detect_task_type(query)
        
        context = CodeContext(language=self.current_language)
        
        if task_type == CodeTaskType.GENERATION:
            result = self.model.generate_code(query, context)
            self._display_code_result(result)
        elif task_type == CodeTaskType.EXPLANATION:
            # Extract code from query or use loaded file
            code = self._extract_code_from_query(query)
            if code:
                result = self.model.explain_code(code, context)
                self._display_explanation(result)
        else:
            # General query - use reasoning
            reasoning_result = self.model.reasoning_engine.reason(query)
            self._display_text(reasoning_result.answer)
    
    # Command handlers
    
    def _cmd_help(self, args: str):
        """Show help"""
        help_text = """
[bold cyan]VersaAI Commands:[/bold cyan]

[yellow]General:[/yellow]
  /help              - Show this help
  /lang <language>   - Set programming language (e.g., python, java)
  /history           - Show conversation history
  /clear             - Clear conversation history
  /quit              - Exit VersaAI

[yellow]Code Operations:[/yellow]
  /generate <desc>   - Generate code from description
  /explain <code>    - Explain code
  /review <code>     - Review code for issues
  /debug <error>     - Debug an error
  /refactor <code>   - Refactor code
  /test <code>       - Generate tests

[yellow]File Operations:[/yellow]
  /load <file>       - Load code from file
  /save <file>       - Save last result to file

[yellow]Natural Language:[/yellow]
  Just type your question or request naturally!
  Examples:
    - "Create a Python function to sort a list"
    - "Explain how quicksort works"
    - "Review this code for bugs"
"""
        if self.console:
            self.console.print(Panel(help_text, border_style="cyan"))
        else:
            print(help_text)
    
    def _cmd_set_language(self, args: str):
        """Set programming language"""
        if not args:
            self._print_error("Usage: /lang <language>")
            return
        
        language = args.strip().lower()
        self.current_language = language
        self._print_success(f"Language set to: {language}")
    
    def _cmd_generate(self, args: str):
        """Generate code"""
        if not args:
            self._print_error("Usage: /generate <description>")
            return
        
        context = CodeContext(language=self.current_language)
        result = self.model.generate_code(args, context, use_reasoning=True)
        self._display_code_result(result)
    
    def _cmd_explain(self, args: str):
        """Explain code"""
        code = args or self._read_multiline_input("Enter code to explain (Ctrl+D when done):")
        
        if not code:
            self._print_error("No code provided")
            return
        
        context = CodeContext(language=self.current_language)
        result = self.model.explain_code(code, context)
        self._display_explanation(result)
    
    def _cmd_review(self, args: str):
        """Review code"""
        code = args or self._read_multiline_input("Enter code to review (Ctrl+D when done):")
        
        if not code:
            self._print_error("No code provided")
            return
        
        context = CodeContext(language=self.current_language)
        result = self.model.review_code(code, context)
        self._display_review(result)
    
    def _cmd_debug(self, args: str):
        """Debug error"""
        if not args:
            code = self._read_multiline_input("Enter code with error (Ctrl+D when done):")
            error = input("Enter error message: ")
        else:
            # Try to parse args
            code = args
            error = input("Enter error message: ")
        
        if not code or not error:
            self._print_error("Need both code and error message")
            return
        
        context = CodeContext(language=self.current_language)
        result = self.model.debug_error(code, error, context)
        self._display_debug_result(result)
    
    def _cmd_refactor(self, args: str):
        """Refactor code"""
        code = args or self._read_multiline_input("Enter code to refactor (Ctrl+D when done):")
        
        if not code:
            self._print_error("No code provided")
            return
        
        context = CodeContext(language=self.current_language)
        result = self.model.refactor_code(code, context)
        self._display_refactor_result(result)
    
    def _cmd_test(self, args: str):
        """Generate tests"""
        code = args or self._read_multiline_input("Enter code to test (Ctrl+D when done):")
        
        if not code:
            self._print_error("No code provided")
            return
        
        context = CodeContext(language=self.current_language)
        result = self.model.generate_tests(code, context)
        self._display_code_result({"code": result["test_code"], "explanation": "Tests generated"})
    
    def _cmd_history(self, args: str):
        """Show conversation history"""
        history = self.model.get_conversation_history()
        
        if not history:
            self._print_info("No conversation history")
            return
        
        if self.console:
            for msg in history:
                role_color = "green" if msg["role"] == "user" else "cyan"
                self.console.print(f"[bold {role_color}]{msg['role'].upper()}:[/bold {role_color}]")
                self.console.print(msg["content"])
                self.console.print()
        else:
            for msg in history:
                print(f"\n{msg['role'].upper()}:")
                print(msg["content"])
    
    def _cmd_clear(self, args: str):
        """Clear conversation history"""
        if self._confirm("Clear conversation history?"):
            self.model.clear_conversation()
            self._print_success("Conversation history cleared")
    
    def _cmd_load_file(self, args: str):
        """Load code from file"""
        if not args:
            self._print_error("Usage: /load <file>")
            return
        
        try:
            filepath = Path(args.strip())
            code = filepath.read_text()
            self.current_file = filepath
            
            # Detect language from extension
            ext_to_lang = {
                '.py': 'python',
                '.js': 'javascript',
                '.java': 'java',
                '.cpp': 'cpp',
                '.c': 'c',
                '.rs': 'rust',
                '.go': 'go',
            }
            
            ext = filepath.suffix.lower()
            if ext in ext_to_lang:
                self.current_language = ext_to_lang[ext]
            
            self._print_success(f"Loaded {filepath} ({len(code)} chars, {self.current_language})")
            
        except Exception as e:
            self._print_error(f"Failed to load file: {e}")
    
    def _cmd_save(self, args: str):
        """Save last result to file"""
        # TODO: Implement result saving
        self._print_info("Save functionality coming soon")
    
    def _cmd_quit(self, args: str):
        """Quit CLI"""
        self.running = False
    
    # Display helpers
    
    def _display_code_result(self, result: dict):
        """Display code generation result"""
        code = result.get("code", "")
        explanation = result.get("explanation", "")
        
        if self.console:
            # Display code with syntax highlighting
            syntax = Syntax(code, self.current_language, theme="monokai", line_numbers=True)
            self.console.print(Panel(syntax, title="Generated Code", border_style="green"))
            
            if explanation:
                self.console.print(Panel(Markdown(explanation), title="Explanation", border_style="blue"))
        else:
            print("\n" + "="*70)
            print("GENERATED CODE:")
            print("="*70)
            print(code)
            if explanation:
                print("\nEXPLANATION:")
                print(explanation)
            print("="*70 + "\n")
    
    def _display_explanation(self, result: dict):
        """Display code explanation"""
        explanation = result.get("explanation", "")
        key_concepts = result.get("key_concepts", [])
        
        if self.console:
            self.console.print(Panel(Markdown(explanation), title="Explanation", border_style="blue"))
            
            if key_concepts:
                table = Table(title="Key Concepts")
                table.add_column("Concept", style="cyan")
                for concept in key_concepts:
                    table.add_row(concept)
                self.console.print(table)
        else:
            print("\nEXPLANATION:")
            print(explanation)
            if key_concepts:
                print("\nKEY CONCEPTS:")
                for concept in key_concepts:
                    print(f"  - {concept}")
    
    def _display_review(self, result: dict):
        """Display code review"""
        issues = result.get("issues", [])
        suggestions = result.get("suggestions", [])
        score = result.get("score", 0)
        
        if self.console:
            # Score panel
            score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
            self.console.print(Panel(
                f"[bold {score_color}]Code Quality Score: {score}/100[/bold {score_color}]",
                border_style=score_color
            ))
            
            # Issues table
            if issues:
                table = Table(title="Issues Found", border_style="red")
                table.add_column("Severity", style="red")
                table.add_column("Issue")
                for issue in issues:
                    table.add_row(issue.get("severity", "Medium"), issue.get("description", ""))
                self.console.print(table)
            
            # Suggestions
            if suggestions:
                self.console.print("\n[bold cyan]Suggestions:[/bold cyan]")
                for sugg in suggestions:
                    self.console.print(f"  • {sugg}")
        else:
            print(f"\nCODE QUALITY SCORE: {score}/100")
            if issues:
                print("\nISSUES:")
                for issue in issues:
                    print(f"  - {issue}")
            if suggestions:
                print("\nSUGGESTIONS:")
                for sugg in suggestions:
                    print(f"  - {sugg}")
    
    def _display_debug_result(self, result: dict):
        """Display debugging result"""
        root_cause = result.get("root_cause", "")
        fix = result.get("fix", "")
        
        if self.console:
            self.console.print(Panel(root_cause, title="Root Cause", border_style="red"))
            
            if fix:
                syntax = Syntax(fix, self.current_language, theme="monokai")
                self.console.print(Panel(syntax, title="Suggested Fix", border_style="green"))
        else:
            print("\nROOT CAUSE:")
            print(root_cause)
            print("\nSUGGESTED FIX:")
            print(fix)
    
    def _display_refactor_result(self, result: dict):
        """Display refactoring result"""
        refactored = result.get("refactored_code", "")
        improvements = result.get("improvements", {})
        
        if self.console:
            syntax = Syntax(refactored, self.current_language, theme="monokai", line_numbers=True)
            self.console.print(Panel(syntax, title="Refactored Code", border_style="green"))
            
            if improvements:
                self.console.print(Panel(str(improvements), title="Improvements", border_style="blue"))
        else:
            print("\nREFACTORED CODE:")
            print(refactored)
            if improvements:
                print("\nIMPROVEMENTS:")
                print(improvements)
    
    def _display_text(self, text: str):
        """Display plain text"""
        if self.console:
            self.console.print(Panel(Markdown(text), border_style="cyan"))
        else:
            print(f"\n{text}\n")
    
    # Utility methods
    
    def _detect_task_type(self, query: str) -> CodeTaskType:
        """Detect task type from query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['generate', 'create', 'write', 'make']):
            return CodeTaskType.GENERATION
        elif any(word in query_lower for word in ['explain', 'what is', 'how does', 'describe']):
            return CodeTaskType.EXPLANATION
        elif any(word in query_lower for word in ['review', 'check', 'analyze']):
            return CodeTaskType.REVIEW
        elif any(word in query_lower for word in ['debug', 'fix', 'error', 'bug']):
            return CodeTaskType.DEBUG
        elif any(word in query_lower for word in ['refactor', 'improve', 'optimize']):
            return CodeTaskType.REFACTOR
        elif any(word in query_lower for word in ['test', 'unittest']):
            return CodeTaskType.TEST
        else:
            return CodeTaskType.GENERATION
    
    def _extract_code_from_query(self, query: str) -> Optional[str]:
        """Extract code from query"""
        # Simple extraction - look for code blocks
        if '```' in query:
            parts = query.split('```')
            if len(parts) >= 3:
                return parts[1].strip()
        return None
    
    def _read_multiline_input(self, prompt: str) -> str:
        """Read multiline input"""
        print(prompt)
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        return '\n'.join(lines)
    
    def _confirm(self, message: str) -> bool:
        """Ask for confirmation"""
        if self.console and RICH_AVAILABLE:
            return Confirm.ask(message)
        else:
            response = input(f"{message} (y/n): ").strip().lower()
            return response in ('y', 'yes')
    
    def _print_success(self, message: str):
        """Print success message"""
        if self.console:
            self.console.print(f"[bold green]✓[/bold green] {message}")
        else:
            print(f"✓ {message}")
    
    def _print_error(self, message: str):
        """Print error message"""
        if self.console:
            self.console.print(f"[bold red]✗[/bold red] {message}")
        else:
            print(f"✗ {message}")
    
    def _print_info(self, message: str):
        """Print info message"""
        if self.console:
            self.console.print(f"[cyan]ℹ[/cyan] {message}")
        else:
            print(f"ℹ {message}")
    
    def _print_goodbye(self):
        """Print goodbye message"""
        if self.console:
            self.console.print("\n[bold cyan]Thanks for using VersaAI! Happy coding! 🚀[/bold cyan]\n")
        else:
            print("\nThanks for using VersaAI! Happy coding! 🚀\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="VersaAI - Intelligent Coding Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Multi-model mode (auto-select best model for each task)
  versaai --multi-model
  
  # Interactive mode (placeholder - no LLM)
  versaai
  
  # With local GGUF model (llama.cpp)
  versaai --provider llama-cpp --model ~/.versaai/models/deepseek-coder-6.7b.gguf
  
  # With HuggingFace model
  versaai --provider huggingface --model bigcode/starcoder2-7b
  
  # With OpenAI API
  versaai --provider openai --model gpt-4-turbo
  
  # With Anthropic Claude API
  versaai --provider anthropic --model claude-3-sonnet-20240229
  
  # Set default language
  versaai --lang rust --provider openai --model gpt-3.5-turbo
  
  # GPU acceleration for local models
  versaai --provider llama-cpp --model ~/.versaai/models/model.gguf --n-gpu-layers -1
        """
    )
    
    parser.add_argument(
        '--lang', '--language',
        default='python',
        help='Default programming language (default: python)'
    )
    
    parser.add_argument(
        '--model-id',
        default='code-assistant-v1',
        help='VersaAI model identifier (default: code-assistant-v1)'
    )
    
    parser.add_argument(
        '--multi-model',
        action='store_true',
        help='Enable multi-model mode: automatically select best model for each task'
    )
    
    parser.add_argument(
        '--provider',
        choices=['llama-cpp', 'huggingface', 'hf', 'openai', 'anthropic'],
        help='LLM provider: llama-cpp (local GGUF), huggingface, openai, or anthropic'
    )
    
    parser.add_argument(
        '--model',
        help='LLM model path (for llama-cpp) or name (for APIs)'
    )
    
    parser.add_argument(
        '--device',
        default='auto',
        help='Device for HuggingFace models: auto, cuda, cpu (default: auto)'
    )
    
    parser.add_argument(
        '--n-gpu-layers',
        type=int,
        default=-1,
        help='Number of GPU layers for llama-cpp models (default: -1 = all GPU layers)'
    )
    
    parser.add_argument(
        '--n-ctx',
        type=int,
        default=8192,
        help='Context size for llama-cpp models (default: 8192)'
    )
    
    parser.add_argument(
        '--n-threads',
        type=int,
        help='Number of CPU threads for llama-cpp (default: auto)'
    )
    
    parser.add_argument(
        '--load-in-8bit',
        action='store_true',
        help='Load HuggingFace model in 8-bit mode (reduces memory)'
    )
    
    parser.add_argument(
        '--load-in-4bit',
        action='store_true',
        help='Load HuggingFace model in 4-bit mode (reduces memory further)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output (for debugging)'
    )
    
    args = parser.parse_args()
    
    # Handle multi-model mode
    if args.multi_model:
        from versaai.models.multi_model_manager import MultiModelManager
        
        print("🚀 Initializing Multi-Model Mode...")
        manager = MultiModelManager()
        
        stats = manager.get_stats()
        if stats['total_models'] == 0:
            print("\n❌ No models found!")
            print(f"   Models directory: {stats['models_dir']}")
            print("\n💡 Download models first:")
            print("   python scripts/download_all_models.py\n")
            sys.exit(1)
        
        # Show available models
        print(f"\n✅ Found {stats['total_models']} model(s):")
        for model in manager.list_models():
            status = "✅" if model['can_run'] else "⚠️ "
            print(f"  {status} {model['name']} ({model['size_gb']:.1f}GB)")
        
        print(f"\n📊 System: {stats['available_ram_gb']:.1f}GB / {stats['total_ram_gb']:.1f}GB RAM available")
        print(f"   {stats['usable_models']} model(s) can run on your system\n")
        
        # Create CLI with multi-model manager
        cli = VersaAICLI(
            model_id=args.model_id,
            llm_provider='multi-model',
            llm_model=None,
            multi_model_manager=manager
        )
    else:
        # Prepare LLM kwargs based on provider
        llm_kwargs = {}
        if args.provider == 'llama-cpp':
            llm_kwargs['n_gpu_layers'] = args.n_gpu_layers
            llm_kwargs['n_ctx'] = args.n_ctx
            if args.n_threads:
                llm_kwargs['n_threads'] = args.n_threads
            llm_kwargs['verbose'] = args.verbose
        elif args.provider in ['huggingface', 'hf']:
            llm_kwargs['device'] = args.device
            llm_kwargs['load_in_8bit'] = args.load_in_8bit
            llm_kwargs['load_in_4bit'] = args.load_in_4bit
        
        # Create and run CLI
        cli = VersaAICLI(
            model_id=args.model_id,
            llm_provider=args.provider,
            llm_model=args.model,
            **llm_kwargs
        )
    
    cli.current_language = args.lang
    
    try:
        cli.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
        sys.exit(0)


if __name__ == '__main__':
    main()
