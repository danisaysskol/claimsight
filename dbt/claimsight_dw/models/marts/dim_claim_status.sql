-- Small conformed dimension for claim adjudication status.
select
    {{ surrogate_key(['status']) }} as claim_status_sk,
    status,
    is_final,
    is_paid_state
from (
    values
        ('Paid',           true,  true),
        ('Partially Paid', true,  true),
        ('Denied',         true,  false),
        ('Pending',        false, false),
        ('In Review',      false, false)
) as s(status, is_final, is_paid_state)
