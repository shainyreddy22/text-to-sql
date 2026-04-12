# Milestone 3: Multi-Table JOIN Testing Documentation

The Sakila database is highly normalized, meaning even basic business questions require complex multi-table JOIN operations. Using the advanced Chain of Thought (CoT) prompting technique implemented during Milestone 1, the dynamic Text-to-SQL bot successfully translates complex, human-readable semantics into valid 5+ table joins natively, without hallucinations.

---

## Test Case 1: 5-Table Aggregation & Grouping
**User Query:** 
> *"List the first and last names of the top 3 customers from Canada who have rented the most movies, along with their total rental count."*

**Tables Required (5):**
1. `customer`
2. `rental`
3. `address`
4. `city`
5. `country`

**Generated AI Thought Process & SQL:**
```sql
/*
THINKING PROCESS:
1. Tables Needed: customer, rental, address, city, country
2. JOIN Conditions:
    - customer.customer_id = rental.customer_id
    - customer.address_id = address.address_id
    - address.city_id = city.city_id
    - city.country_id = country.country_id
3. Columns to Select: customer.first_name, customer.last_name, COUNT(rental.rental_id)
4. Filters: country.country = 'Canada'
5. Group/Order: GROUP BY customer_id, ORDER BY total_rentals DESC LIMIT 3
*/
SELECT 
    T1.first_name, 
    T1.last_name, 
    COUNT(T2.rental_id) as total_rentals
FROM customer AS T1
JOIN rental AS T2 ON T1.customer_id = T2.customer_id
JOIN address AS T3 ON T1.address_id = T3.address_id
JOIN city AS T4 ON T3.city_id = T4.city_id
JOIN country AS T5 ON T4.country_id = T5.country_id
WHERE T5.country = 'Canada'
GROUP BY T1.customer_id
ORDER BY total_rentals DESC
LIMIT 3;
```
**Status Verification:** ✅ Passed successfully. The engine natively bridges the gap between customer geographic data (`country`) and their active rental history (`rental`), grouping correctly.

---

## Test Case 2: 6-Table Complex Relationship Filtering
**User Query:** 
> *"Which customers living in the city of London have ever rented the specific movie 'ACADEMY DINOSAUR'?"*

**Tables Required (6):**
1. `customer`
2. `address`
3. `city`
4. `rental`
5. `inventory`
6. `film`

**Status Verification:** ✅ Passed successfully. The CoT engine flawlessly mapped the long relationship chain—crossing from geographic identity (`city`) all the way down to physical distribution identity (`inventory` and `film`), successfully preventing hallucinated tables or shortcuts!
