-- DDLs
--    CREATE TABLE IF NOT EXISTS realtime_market_data (
--         exchange VARCHAR,
--         trading_symbol VARCHAR,
--         symbol_token VARCHAR,
--         ltp DECIMAL(18,6),
--         open DECIMAL(18,6),
--         high DECIMAL(18,6),
--         low DECIMAL(18,6),
--         close DECIMAL(18,6),
--         last_trade_qty INTEGER,
--         exch_feed_time TIMESTAMP,
--         exch_trade_time TIMESTAMP,
--         net_change DECIMAL(18,6),
--         percent_change DECIMAL(18,6),
--         avg_price DECIMAL(18,6),
--         trade_volume BIGINT,
--         opn_interest BIGINT,
--         lower_circuit DECIMAL(18,6),
--         upper_circuit DECIMAL(18,6),
--         tot_buy_quan BIGINT,
--         tot_sell_quan BIGINT,
--         week_low_52 DECIMAL(18,6),
--         week_high_52 DECIMAL(18,6),
--         depth_json TEXT,
--         timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--         PRIMARY KEY (symbol_token, timestamp)
--     )
select *
from(
        select row_number() over(
                PARTITION BY symbol_token
                ORDER BY timestamp DESC
            ) as rn,
            exchange,
            trading_symbol,
            ltp,
            open,
            high,
            low,
            close,
            exch_feed_time,
            exch_trade_time,
            net_change,
            percent_change,
            trade_volume,
            opn_interest,
            lower_circuit,
            upper_circuit,
            tot_buy_quan,
            tot_sell_quan,
            week_low_52,
            week_high_52,
            timestamp
        FROM realtime_market_data rmd
    )
WHERE rn = 1 -- Summary View SQL Query
    -- This view joins token_master and realtime_market_data to provide a comprehensive market summary
CREATE OR REPLACE VIEW market_summary AS WITH -- Get latest equity data
    equity_data AS (
        SELECT tm.token AS equity_token,
            tm.symbol AS equity_symbol,
            tm.name AS equity_name,
            tm.futures_token,
            rmd.ltp AS equity_price,
            rmd.percent_change AS equity_percent_change,
            rmd.week_high_52 AS equity_52w_high,
            rmd.week_low_52 AS equity_52w_low
        FROM token_master tm
            LEFT JOIN realtime_market_data rmd ON tm.token = rmd.symbol_token
        WHERE tm.token_type = 'EQUITY'
            AND rmd.latest_record_flag = TRUE
    ),
    -- Get latest futures data
    futures_data AS (
        SELECT tm.token AS futures_token,
            rmd.ltp AS futures_price,
            rmd.percent_change AS futures_percent_change
        FROM token_master tm
            LEFT JOIN realtime_market_data rmd ON tm.token = rmd.symbol_token
        WHERE tm.token_type = 'FUTURES'
            AND rmd.latest_record_flag = TRUE
    ),
    -- Get ATM call options
    atm_call_options AS (
        SELECT tm.futures_token,
            rmd.ltp AS ce_price
        FROM token_master tm
            LEFT JOIN realtime_market_data rmd ON tm.token = rmd.symbol_token
        WHERE tm.instrumenttype = 'OPTIDX'
            AND tm.token LIKE '%CE%' -- Logic to determine ATM options based on strike price vs futures price
            -- This is a placeholder - you may need to refine this logic
            AND rmd.latest_record_flag = TRUE
    ),
    -- Get ATM put options
    atm_put_options AS (
        SELECT tm.futures_token,
            rmd.ltp AS pe_price
        FROM token_master tm
            LEFT JOIN realtime_market_data rmd ON tm.token = rmd.symbol_token
        WHERE tm.instrumenttype = 'OPTIDX'
            AND tm.token LIKE '%PE%' -- Logic to determine ATM options based on strike price vs futures price
            -- This is a placeholder - you may need to refine this logic
            AND rmd.latest_record_flag = TRUE
    ) -- Final select joining all CTEs
SELECT ed.equity_token,
    ed.equity_symbol,
    ed.equity_name,
    ed.equity_price,
    ed.equity_percent_change,
    ed.equity_52w_high,
    ed.equity_52w_low,
    fd.futures_price,
    fd.futures_percent_change,
    COALESCE(ac.ce_price, 0) + COALESCE(ap.pe_price, 0) AS atm_total_price,
    COALESCE(ac.ce_price, 0) AS atm_ce_price,
    COALESCE(ap.pe_price, 0) AS atm_pe_price
FROM equity_data ed
    LEFT JOIN futures_data fd ON ed.futures_token = fd.futures_token
    LEFT JOIN atm_call_options ac ON ed.futures_token = ac.futures_token
    LEFT JOIN atm_put_options ap ON ed.futures_token = ap.futures_token
ORDER BY ed.equity_symbol;