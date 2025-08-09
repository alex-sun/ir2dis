#!/usr/bin/env python3
"""
Metrics collection for iRacing → Discord Auto-Results Bot.
"""

class Metrics:
    """Collection of metrics counters."""
    
    def __init__(self):
        self.poll_cycles_total = 0
        self.results_fetched_total = 0
        self.posts_published_total = 0
        self.dedupe_skips_total = 0
        self.auth_failures_total = 0
        self.captcha_required_total = 0
        self.rate_limited_total = 0
        
    def increment_poll_cycle(self):
        """Increment poll cycle counter."""
        self.poll_cycles_total += 1
        
    def increment_results_fetched(self):
        """Increment results fetched counter."""
        self.results_fetched_total += 1
        
    def increment_posts_published(self):
        """Increment posts published counter."""
        self.posts_published_total += 1
        
    def increment_dedupe_skips(self):
        """Increment deduplication skips counter."""
        self.dedupe_skips_total += 1
        
    def increment_auth_failures(self):
        """Increment authentication failures counter."""
        self.auth_failures_total += 1
        
    def increment_captcha_required(self):
        """Increment CAPTCHA required counter."""
        self.captcha_required_total += 1
        
    def increment_rate_limited(self):
        """Increment rate limited counter."""
        self.rate_limited_total += 1

# Global metrics instance
metrics = Metrics()
