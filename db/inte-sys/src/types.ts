/** Rows exposed by the tables declared in sql/schema.sql. */
export interface Paper {
	id: string;
	doi: string | null;
	title: string | null;
	title_zh: string | null;
	abstract: string | null;
	abstract_zh: string | null;
	authors: string | null;
	keywords: string | null;
	keywords_zh: string | null;
	venue: string | null;
	issn: string | null;
	volume: string | null;
	issue: string | null;
	year: number | null;
	n_citation: number | null;
}

export interface Organization {
	id: string;
	name: string;
	name_en: string | null;
	name_zh: string | null;
	type: string | null;
	acronyms: string | null;
	aliases: string | null;
	details: string | null;
	location: string | null;
	url: string | null;
	image: string | null;
}

export interface PaperAuthor {
	paperid: string;
	name: string | null;
	name_zh: string | null;
	org: string | null;
	org_zh: string | null;
}

export interface PaperWithAuthors extends Paper {
	author_rows: PaperAuthor[];
}

export interface Pagination {
	limit: number;
	offset: number;
}

export interface PagedResult<T> {
	rows: T[];
	total: number;
}

