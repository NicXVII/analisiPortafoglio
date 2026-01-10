"""
Script per aggiornare import paths dopo riorganizzazione package.
Aggiorna tutti gli import da old paths a new paths nella struttura src/portfolio_engine/.
"""

import os
import re
from pathlib import Path

# Mapping: old module name → new module path
IMPORT_MAPPINGS = {
    # Utils
    'logger': 'portfolio_engine.utils.logger',
    'exceptions': 'portfolio_engine.utils.exceptions',
    'transaction_costs': 'portfolio_engine.utils.costs',
    
    # Models
    'models': 'portfolio_engine.models.portfolio',
    
    # Data definitions
    'crisis_definitions': 'portfolio_engine.data.definitions.crisis',
    'taxonomy': 'portfolio_engine.data.definitions.taxonomy',
    
    # Data layer
    'data': 'portfolio_engine.data.loader',
    
    # Analytics
    'regime_detection': 'portfolio_engine.analytics.regime',
    'metrics': 'portfolio_engine.analytics.metrics_monolith',
    'analysis': 'portfolio_engine.analytics.analysis_monolith',
    
    # Decision
    'gate_system': 'portfolio_engine.decision.gate_system',
    'risk_intent': 'portfolio_engine.decision.risk_intent',
    'validation': 'portfolio_engine.decision.validation',
    
    # Reporting
    'output': 'portfolio_engine.reporting.console',
    'export': 'portfolio_engine.reporting.export',
    
    # Config
    'config': 'portfolio_engine.config.user_config',
    'threshold_documentation': 'portfolio_engine.config.thresholds',
    
    # Core
    'pipeline': 'portfolio_engine.core.pipeline',
    'main': 'portfolio_engine.core.main_legacy',
}


def update_imports_in_file(filepath: Path) -> tuple[int, list[str]]:
    """
    Aggiorna gli import in un file.
    
    Returns:
        (num_changes, list_of_changes)
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    for old_module, new_module in IMPORT_MAPPINGS.items():
        # Pattern 1: from old_module import ...
        pattern1 = rf'\bfrom {old_module}(\s+import\s+)'
        replacement1 = rf'from {new_module}\1'
        new_content = re.sub(pattern1, replacement1, content)
        if new_content != content:
            changes.append(f"  • from {old_module} import → from {new_module} import")
            content = new_content
        
        # Pattern 2: import old_module
        pattern2 = rf'\bimport {old_module}\b'
        replacement2 = f'import {new_module}'
        new_content = re.sub(pattern2, replacement2, content)
        if new_content != content:
            changes.append(f"  • import {old_module} → import {new_module}")
            content = new_content
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return len(changes), changes


def main():
    """Aggiorna tutti i file nella struttura src/ e tests/"""
    
    base_dir = Path('src/portfolio_engine')
    test_dir = Path('tests')
    
    total_files = 0
    total_changes = 0
    
    print("=" * 70)
    print("AGGIORNAMENTO IMPORT PATHS")
    print("=" * 70)
    print()
    
    # Process src/
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                filepath = Path(root) / file
                num_changes, changes = update_imports_in_file(filepath)
                
                if num_changes > 0:
                    total_files += 1
                    total_changes += num_changes
                    print(f"📝 {filepath.relative_to(base_dir.parent)}")
                    for change in changes:
                        print(change)
                    print()
    
    # Process tests/
    for root, dirs, files in os.walk(test_dir):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                filepath = Path(root) / file
                num_changes, changes = update_imports_in_file(filepath)
                
                if num_changes > 0:
                    total_files += 1
                    total_changes += num_changes
                    print(f"📝 {filepath}")
                    for change in changes:
                        print(change)
                    print()
    
    print("=" * 70)
    print(f"✅ Completato!")
    print(f"   File modificati: {total_files}")
    print(f"   Import aggiornati: {total_changes}")
    print("=" * 70)


if __name__ == '__main__':
    main()
