const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
export const formatMoney = (n: number) => money.format(n)

export const STATUS_LABEL: Record<string, string> = {
  open: 'OPEN',
  awaiting_approval: 'AWAITING APPROVAL',
  resolved: 'RESOLVED',
}

export const TYPE_LABEL: Record<string, string> = {
  customer_order: 'CUSTOMER ORDER',
  rent_notice: 'RENT NOTICE',
  price_override: 'PRICE OVERRIDE',
}
