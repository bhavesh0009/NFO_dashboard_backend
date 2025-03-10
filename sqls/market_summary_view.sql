-- Market Summary View SQL Query
-- This view joins token_master and realtime_market_data to provide a comprehensive market summary
-- including equity data, futures data and ATM options data
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
            AND tm.token LIKE '%CE%' -- Find options closest to the current price (ATM options)
            AND EXISTS (
                SELECT 1
                FROM token_master tm2
                    JOIN realtime_market_data rmd2 ON tm2.token = rmd2.symbol_token
                WHERE tm2.token_type = 'FUTURES'
                    AND tm2.token = tm.futures_token
                    AND ABS(tm.strike - rmd2.ltp) < tm.strike_distance
                    AND rmd2.latest_record_flag = TRUE
            )
            AND rmd.latest_record_flag = TRUE
    ),
    -- Get ATM put options
    atm_put_options AS (
        SELECT tm.futures_token,
            rmd.ltp AS pe_price
        FROM token_master tm
            LEFT JOIN realtime_market_data rmd ON tm.token = rmd.symbol_token
        WHERE tm.instrumenttype = 'OPTIDX'
            AND tm.token LIKE '%PE%' -- Find options closest to the current price (ATM options)
            AND EXISTS (
                SELECT 1
                FROM token_master tm2
                    JOIN realtime_market_data rmd2 ON tm2.token = rmd2.symbol_token
                WHERE tm2.token_type = 'FUTURES'
                    AND tm2.token = tm.futures_token
                    AND ABS(tm.strike - rmd2.ltp) < tm.strike_distance
                    AND rmd2.latest_record_flag = TRUE
            )
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