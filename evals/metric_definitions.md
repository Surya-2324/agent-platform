# Metric definitions (v1)

The agent and the eval set must use these definitions. If a question uses a term
differently, the agent must state the assumption it made.

## Data coverage
- Orders run from July 1996 to May 1998 (1996 and 1998 are partial years).
- The data has no "today": relative dates ("last year", "this month") must be stated
  as an explicit assumption or clarified with the user.

## Revenue
revenue = SUM(order_details.unit_price × order_details.quantity × (1 − order_details.discount))
- Uses the price on the order line (what the customer actually paid),
  NOT products.unit_price (the current list price).
- Excludes freight.
- Calculated in exact decimals (Postgres `numeric`), rounded to 2 decimal places only at the end.

## Dates
- A sale belongs to the year/month of `orders.order_date` (not shipped_date).
- "In 1997" means order_date >= '1997-01-01' AND order_date < '1998-01-01'.

## Customers
- A customer is a company in `customers`, identified by `company_name`.
- "Best customers" (default) = top 5 customers by all-time revenue.

## Products
- A product's "price" = list price `products.unit_price`.
- Discontinued = `products.discontinued = 1`.
- Stock = `products.units_in_stock`.

## Employees
- Employee name = first_name + ' ' + last_name.
- An employee is credited with the revenue of orders where `orders.employee_id` matches.

## Not available in this data
- Costs, profit or margin · marketing campaigns · website data · anything after May 1998.
