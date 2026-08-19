import numpy as np


def validate_score_distribution(results):
    """Validate score distribution and warn about potential inflation."""
    if not results:
        return {}
    scores = [s.get('Score', 0) for s in results if s.get('Score', 0) > 0]
    total = len(scores)
    if total == 0:
        return {}
    
    dist = {
        '90-100': len([s for s in scores if s >= 90]),
        '80-89':  len([s for s in scores if 80 <= s < 90]),
        '70-79':  len([s for s in scores if 70 <= s < 80]),
        '60-69':  len([s for s in scores if 60 <= s < 70]),
        '<60':    len([s for s in scores if s < 60]),
    }
    
    pct_90 = (dist['90-100'] / total) * 100
    pct_80_plus = ((dist['90-100'] + dist['80-89']) / total) * 100
    
    print(f"\n{'='*50}")
    print(" SCORE DISTRIBUTION (V3.1 Validation)")
    print(f"{'='*50}")
    for bracket, count in dist.items():
        pct = (count / total) * 100
        bar = '' * int(pct / 2)
        print(f"  {bracket:>6}: {count:>4} ({pct:5.1f}%) {bar}")
    print(f"  Total: {total}")
    
    if pct_90 > 10:
        print(f"    WARNING: {pct_90:.1f}% scored 90+ (expect <10%)  possible grade inflation")
    if pct_80_plus > 30:
        print(f"    WARNING: {pct_80_plus:.1f}% scored 80+ (expect <30%)  review scoring weights")
    
    if pct_90 <= 10 and pct_80_plus <= 30:
        print("   Distribution looks healthy")
    print(f"{'='*50}")
    
    return dist
