with spine as (
    select
        dateadd('day', seq4(), '2023-01-01'::date) as date_day
    from table(generator(rowcount => 1095))
)

select
    date_day,
    date_trunc('month', date_day)   as month_start,
    date_trunc('quarter', date_day) as quarter_start,
    year(date_day)                  as year,
    month(date_day)                 as month_num,
    quarter(date_day)               as quarter_num,
    to_char(date_day, 'Mon YYYY')   as month_label
from spine
