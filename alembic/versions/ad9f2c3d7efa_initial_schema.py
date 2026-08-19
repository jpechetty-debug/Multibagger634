"""Initial schema

Revision ID: ad9f2c3d7efa
Revises: 
Create Date: 2026-08-19 07:15:39.778229

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad9f2c3d7efa'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('''
        CREATE TABLE IF NOT EXISTS multibaggers (
            symbol TEXT PRIMARY KEY,
            price REAL,
            sector TEXT,
            score INTEGER,
            f_score INTEGER,
            rating TEXT,
            buy_below REAL,
            stop_loss REAL,
            target_1 REAL,
            target_2 REAL,
            sales_growth REAL,
            roe REAL,
            peg_ratio REAL,
            debt_equity REAL,
            rsi REAL,
            smart_money REAL,
            market_cap_cr REAL,
            cfo_pat_ratio REAL,
            sales_cagr_5y REAL,
            avg_roe_5y REAL,
            pe_ratio REAL,
            down_from_52w REAL,
            rs_rating REAL,
            earnings_accel INTEGER,
            sector_leader INTEGER,
            graham_number REAL,
            value_gap REAL,
            technical_signal TEXT,
            analyst_rating TEXT,
            analyst_upside REAL,
            promoter_holding REAL,
            inst_holding REAL,
            atr REAL,
            stop_loss_atr REAL,
            max_qty_1l REAL,
            as_of_date TEXT,
            last_audited TIMESTAMP,
            updated_at TIMESTAMP,
            conviction_score REAL,
            conviction_boost REAL,
            institutional_interest INTEGER,
            super_investors TEXT,
            backtest_cagr REAL,
            backtest_win_rate REAL,
            backtest_max_dd REAL,
            backtest_sharpe REAL,
            high_52w REAL,
            low_52w REAL,
            pledge_pct REAL,
            piotroski_score INTEGER,
            CHECK(pe_ratio >= -100 AND pe_ratio <= 1000),
            CHECK(roe >= -500 AND roe <= 500),
            CHECK(score >= 0 AND score <= 100)
        )
    ''')
    op.execute('''
        CREATE TABLE IF NOT EXISTS score_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_score REAL,
            close_price REAL,
            pe_ratio REAL,
            FOREIGN KEY (symbol) REFERENCES multibaggers (symbol)
        )
    ''')
    op.execute('''
        CREATE TABLE IF NOT EXISTS factor_penalties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            penalty_name TEXT,
            penalty_value REAL,
            FOREIGN KEY (symbol) REFERENCES multibaggers (symbol)
        )
    ''')
    op.execute('''
        CREATE TABLE IF NOT EXISTS valuation_metrics (
            symbol TEXT PRIMARY KEY,
            dcf_value REAL,
            graham_value REAL,
            epv_value REAL,
            intrinsic_value REAL,
            margin_of_safety REAL,
            verdict TEXT,
            confidence_score INTEGER,
            as_of_date TEXT,
            calculated_at TIMESTAMP,
            FOREIGN KEY (symbol) REFERENCES multibaggers (symbol)
        )
    ''')
    op.execute('''
        CREATE TABLE IF NOT EXISTS microcaps (
            symbol TEXT PRIMARY KEY,
            price REAL,
            score INTEGER,
            market_cap REAL,
            sales_growth REAL,
            promoter_holding REAL,
            buy_zone TEXT,
            stop_loss REAL,
            target_1 REAL,
            target_2 REAL,
            updated_at TIMESTAMP
        )
    ''')
    op.execute('''
        CREATE TABLE IF NOT EXISTS executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            side TEXT,
            expected_price REAL,
            fill_price REAL,
            slippage_bps REAL,
            liquidity_tier TEXT,
            regime TEXT,
            vix REAL,
            timestamp TIMESTAMP,
            source TEXT
        )
    ''')
    op.execute('''
        CREATE TABLE IF NOT EXISTS slippage_metrics (
            tier TEXT,
            time_window TEXT,
            regime TEXT,
            p50_bps REAL,
            p75_bps REAL,
            p95_bps REAL,
            count INTEGER,
            updated_at TIMESTAMP,
            PRIMARY KEY (tier, time_window, regime)
        )
    ''')
    op.execute('''
        CREATE TABLE IF NOT EXISTS buy_thesis (
            symbol TEXT PRIMARY KEY,
            buy_date TEXT,
            primary_driver TEXT,
            revenue_growth_min REAL,
            operating_margin_min REAL,
            score_at_buy REAL,
            checklist_passes_at_buy INTEGER,
            regime_at_buy TEXT,
            raw_thesis_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    op.execute('''
        CREATE TABLE IF NOT EXISTS fundamentals_pit (
            symbol TEXT NOT NULL,
            as_of_date TEXT NOT NULL,
            price REAL,
            sector TEXT,
            score INTEGER,
            sales_cagr_5y REAL,
            avg_roe_5y REAL,
            pe_ratio REAL,
            debt_equity REAL,
            market_cap_cr REAL,
            cfo_pat_ratio REAL,
            high_52w REAL,
            low_52w REAL,
            roce REAL,
            median_pat_growth REAL,
            ret_1m REAL,
            ret_3m REAL,
            ret_6m REAL,
            vol_breakout REAL,
            dist_from_52w_high REAL,
            ml_rank_score REAL,
            source_updated_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (symbol, as_of_date)
        )
    ''')
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_fundamentals_pit_as_of_date
        ON fundamentals_pit (as_of_date)
    ''')


def downgrade() -> None:
    op.drop_table('buy_thesis')
    op.drop_table('slippage_metrics')
    op.drop_table('executions')
    op.drop_table('microcaps')
    op.drop_table('valuation_metrics')
    op.drop_table('factor_penalties')
    op.drop_table('score_history')
    op.drop_table('fundamentals_pit')
    op.drop_table('multibaggers')
