with equity_master as (
    select tm.token,
        tm.symbol,
        tm.name,
        tm.futures_token
    from token_master tm
    where token_type = 'EQUITY'
),
futures_master as (
    select tm.token,
        tm.name,
        cast(tm.expiry as date) as expiry,
        tm.expiry,
        tm.lotsize
    from token_master tm
    where token_type = 'FUTURES'
),
realtime_equity_latest as(
    with realtime_equity as(
        select rmd.trading_symbol,
            rmd.symbol_token,
            rmd.ltp,
            rmd.net_change,
            rmd.percent_change,
            rmd.open,
            rmd.high,
            rmd.low,
            rmd.close,
            rmd.trade_volume,
            rmd.opn_interest,
            rmd.week_low_52,
            rmd.week_high_52,
            ROW_NUMBER() OVER(
                PARTITION BY rmd.symbol_token
                ORDER BY rmd.timestamp DESC
            ) as rn
        FROM realtime_market_data rmd
        where exchange = 'NSE'
    )
    select trading_symbol,
        substr(trading_symbol, 1, length(trading_symbol) - 3) AS name,
        ltp,
        percent_change,
        open,
        high,
        low,
        close,
        trade_volume volume,
        opn_interest,
        week_low_52,
        week_high_52
    from realtime_equity re
    where rn = 1
),
realtime_futures_latest as (
    with realtime_futures as (
        select exchange,
            trading_symbol,
            symbol_token,
            ltp futures_ltp,
            percent_change futures_percent_change,
            trade_volume futures_volume,
            opn_interest futures_oi,
            ROW_NUMBER() OVER(
                PARTITION BY rmd.symbol_token
                ORDER BY rmd.timestamp DESC
            ) as rn
        from realtime_market_data rmd
        where rmd.exchange = 'NFO'
            and rmd.trading_symbol like '%FUT'
    )
    select trading_symbol,
        symbol_token,
        futures_ltp,
        futures_percent_change,
        futures_volume,
        futures_oi
    from realtime_futures rf
    where rf.rn = 1
),
realtime_options_latest as (
    select underlying_name,
        sum(ltp) atm_price
    from(
            SELECT rmd.symbol_token,
                regexp_extract(rmd.trading_symbol, '^([^0-9]+)', 1) AS underlying_name,
                substr(rmd.trading_symbol, -2) AS option_type,
                rmd.exchange,
                rmd.ltp,
                rmd.open,
                rmd.high,
                rmd.low,
                rmd.close,
                rmd.exch_feed_time,
                rmd.exch_trade_time,
                rmd.net_change,
                rmd.percent_change,
                rmd.trade_volume,
                rmd.opn_interest,
                row_number() over(
                    partition by regexp_extract(rmd.trading_symbol, '^([^0-9]+)', 1),
                    substr(rmd.trading_symbol, -2)
                    order by timestamp desc
                ) rn
            FROM realtime_market_data rmd
            where rmd.exchange = 'NFO'
                and rmd.trading_symbol not like '%FUT'
        )
    where rn = 1
    group by 1
),
technical_indicators_latest as (
    /* Get the latest technical indicators for each equity token */
    select token,
        symbol_name,
        trade_date,
        sma_50,
        sma_100,
        sma_200,
        ema_20,
        ema_50,
        ema_200,
        rsi_14,
        rsi_21,
        volatility_21,
        volatility_200,
        last_close,
        last_volume
    from technical_indicators_summary tis
)
select em.token,
    em.symbol,
    em.name,
    em.futures_token,
    fm.lotsize,
    fm.expiry,
    rel.ltp,
    rel.percent_change,
    rel.open,
    rel.high,
    rel.low,
    rel.close,
    rel.volume,
    rel.opn_interest,
    rel.week_low_52,
    rel.week_high_52,
    rfl.futures_ltp,
    rfl.futures_percent_change,
    rfl.futures_volume,
    rfl.futures_oi,
    rol.atm_price,
    rol.atm_price * fm.lotsize as atm_price_per_lot,
    ROUND(
        (
            (rel.ltp - rel.week_low_52) / (rel.week_high_52 - rel.week_low_52) * 200
        ) - 100,
        2
    ) AS position_metric,
    /* Technical indicators */
    til.sma_50,
    til.sma_100,
    til.sma_200,
    til.ema_20,
    til.ema_50,
    til.ema_200,
    til.rsi_14,
    til.rsi_21,
    til.volatility_21,
    til.volatility_200,
    /* Calculate indicator-based metrics */
    CASE
        WHEN rel.ltp > til.sma_200 THEN 'ABOVE_SMA200'
        WHEN rel.ltp < til.sma_200 THEN 'BELOW_SMA200'
        ELSE 'AT_SMA200'
    END AS sma_200_position,
    CASE
        WHEN til.sma_50 > til.sma_200 THEN 'BULLISH_CROSSOVER'
        WHEN til.sma_50 < til.sma_200 THEN 'BEARISH_CROSSOVER'
        ELSE 'NEUTRAL'
    END AS ma_crossover_status,
    ROUND((rel.ltp - til.sma_200) / til.sma_200 * 100, 2) AS sma_200_percent_diff
from equity_master em
    left outer join futures_master fm on em.futures_token = fm.token
    left outer join realtime_equity_latest rel on em.name = rel.name
    left outer join realtime_futures_latest rfl on fm.token = rfl.symbol_token
    left outer join realtime_options_latest rol on em.name = rol.underlying_name
    left outer join technical_indicators_latest til on em.token = til.token