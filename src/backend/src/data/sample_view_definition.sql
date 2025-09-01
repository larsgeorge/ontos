-- Sample View: main.marketing.campaign_view
SELECT
    c.campaign_id,
    c.campaign_name,
    SUM(s.amount) AS total_sales_amount,
    COUNT(DISTINCT s.customer_id) AS unique_customers
FROM
    main.sales.orders s
JOIN
    main.marketing.campaigns c ON s.campaign_id = c.campaign_id
WHERE
    s.order_date BETWEEN c.start_date AND c.end_date
GROUP BY
    c.campaign_id,
    c.campaign_name
ORDER BY
    total_sales_amount DESC; 