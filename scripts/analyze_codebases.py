#!/usr/bin/env python3
"""
Code Analysis Runner
Runs analysis on two codebases and generates a detailed report
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from code_metrics import CodeMetrics

# Set up logging
logging.basicConfig(

logger=logging.getLogger(__name__
class CodebaseAnalyzer:
    def __init__(self, codebase1_path: str, codebase2_path: str):

        if not self.codebase1_path.exists() or not self.codebase2_path.exists():
            raise ValueError("One or both codebase paths do not exist"
            def analyze(self) -> Dict[str, Any]:
                """Run analysis on both codebases"""
                logger.info("Starting codebase analysis..."
                results={
                'timestamp': datetime.now().isoformat(),
                'codebase1': self._analyze_codebase(self.codebase1_path),
                'codebase2': self._analyze_codebase(self.codebase2_path),
                'comparison': self._compare_codebases(

                logger.info("Analysis complete"
            return results

            def _analyze_codebase(self, codebase_path: Path) -> Dict[str, Any}:
                """Analyze a single codebase"""
                logger.info(f"Analyzing codebase: {codebase_path}"
            return {
            'complexity': self.metrics.calculate_complexity(codebase_path},
            'duplication': self.metrics.find_duplication(codebase_path],
            'naming': self.metrics.analyze_naming(codebase_path),
            'structure': self.metrics.analyze_structure(codebase_path),
            'async_usage': self.metrics.find_async_usage(codebase_path),
            'caching': self.metrics.find_caching_usage(codebase_path),
            'resource_usage': self.metrics.analyze_resource_usage(codebase_path

            def _compare_codebases(self) -> Dict[str, Any]:
                """Compare the two codebases"""
                comparison={
                'recommendation': '',
                'rationale': [},
                'strengths': {
                'codebase1': [},
                'codebase2': []},
                'weaknesses': {
                'codebase1': [},
                'codebase2': []

                # Compare complexity
                self._compare_metric(
                'complexity',
                'cyclomatic_complexity',
                'Lower cyclomatic complexity',
                comparison

                # Compare duplication
                self._compare_metric(
                'duplication',
                'duplication_percentage',
                'Lower code duplication',
                comparison,
                lower_is_better=True

                # Compare naming conventions
                self._compare_metric(
                'naming',
                'naming_score',
                'Better naming conventions',
                comparison

                # Compare structure
                self._compare_metric(
                'structure',
                'avg_function_size',
                'Better function size',
                comparison,
                lower_is_better=True

                # Compare async usage
                self._compare_metric(
                'async_usage',
                'async_score',
                'Better async/await usage',
                comparison

                # Compare caching
                self._compare_metric(
                'caching',
                'cache_score',
                'Better caching implementation',
                comparison

                # Compare resource usage
                self._compare_metric(
                'resource_usage',
                'resource_score',
                'Better resource usage',
                comparison

                # Generate recommendation

            return comparison

            def _compare_metric(:
            pass
            self,
            category: str,
            metric: str,
            description: str,
            comparison: Dict[str, Any],):
            """Compare a specific metric between codebases"""
            value1=self._get_metric_value(category, metric, 'codebase1'
            value2=self._get_metric_value(category, metric, 'codebase2'
            if value1 is None or value2 is None:
            return

            if (lower_is_better and value1 < value2) or (
                not lower_is_better and value1 > value2):
                comparison['strengths']['codebase1'].append(f"{description} ({metric}: {value1:.2f} vs {value2:.2f})"
                comparison['weaknesses']['codebase2'].append(f"Worse {description} ({metric}: {value2:.2f} vs {value1:.2f})"
                elif (lower_is_better and value2 < value1) or (not lower_is_better and value2 > value1):
                    comparison['strengths']['codebase2'].append(f"{description} ({metric}: {value2:.2f} vs {value1:.2f})"
                    comparison['weaknesses']['codebase1'].append(f"Worse {description} ({metric}: {value1:.2f} vs {value2:.2f})"
                    def _get_metric_value(self, category: str, metric: str,:
                    pass
                    codebase: str) -> float:
                    """Get a specific metric value from the analysis results"""
                    try:
                    return self._analyze_codebase(getattr(self, f"{codebase}_path"))[
                    category][metric]
                    except (KeyError, AttributeError):
                    return None

                    def _generate_recommendation(self, comparison: Dict[str, Any]) -> str:
                        """Generate a recommendation based on the comparison"""
                        strengths1=len(comparison['strengths']['codebase1']
                        strengths2=len(comparison['strengths']['codebase2']
                        if strengths1 > strengths2:
                        return "Recommend keeping codebase1"
                        elif strengths2 > strengths1:
                        return "Recommend keeping codebase2"
                        else:
                        return "Both codebases have similar strengths and weaknesses. Consider keeping the more recent one."

                        def main():
                            print("Usage: python analyze_codebases.py <codebase1_path> <codebase2_path>"
                            sys.exit(1
                            try:
                                analyzer=CodebaseAnalyzer(sys.argv[1], sys.argv[2]
                                results=analyzer.analyze(
                                # Save results to file
                                output_file=f"codebase_analysis_{
                                datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                                with open(output_file, 'w') as f:

                                print(f"\nAnalysis complete. Results saved to {output_file}"
                                print("\nRecommendation:", results['comparison']['recommendation']
                                # Print strengths and weaknesses
                                print("\nCodebase 1:"
                                print("Strengths:", ", ".join(results['comparison']['strengths']['codebase1']
                                print("Weaknesses:", ", ".join(results['comparison']['weaknesses']['codebase1']
                                print("\nCodebase 2:"
                                print("Strengths:", ", ".join(results['comparison']['strengths']['codebase2']
                                print("Weaknesses:", ", ".join(results['comparison']['weaknesses']['codebase2']
                                except Exception as e:
                                    logger.error(f"Error during analysis: {str(e)}"
                                    sys.exit(1
                                    main(
