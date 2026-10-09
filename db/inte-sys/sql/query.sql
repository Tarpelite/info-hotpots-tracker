-- Cloudflare D1 simple queries for the AMiner data.

-- paper_detail_cleaned.csv -> paper
SELECT * FROM paper LIMIT 10;

-- organization_detail_cleaned.csv -> organization
SELECT * FROM organization LIMIT 10;

-- paper_author_cleaned.csv -> paper_author
SELECT * FROM paper_author LIMIT 10;
