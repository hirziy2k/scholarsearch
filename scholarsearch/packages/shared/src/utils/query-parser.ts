// ============================================
// Deterministic Boolean Query AST Parser
// ============================================
//
// Parses a user's Boolean query string into an AST once,
// then compiles it into native syntax for each academic API.
//
// Supports: AND, OR, NOT, parenthetical grouping, quoted phrases.
// LLMs are NEVER used for syntax translation — only for concept expansion.

// ============================================
// Tokenizer
// ============================================

export type TokenType = "TERM" | "PHRASE" | "AND" | "OR" | "NOT" | "LPAREN" | "RPAREN" | "EOF";

export interface Token {
  type: TokenType;
  value: string;
  position: number;
}

export function tokenize(query: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;

  while (i < query.length) {
    // Skip whitespace
    if (/\s/.test(query[i]!)) {
      i++;
      continue;
    }

    // Parentheses
    if (query[i] === "(") {
      tokens.push({ type: "LPAREN", value: "(", position: i });
      i++;
      continue;
    }
    if (query[i] === ")") {
      tokens.push({ type: "RPAREN", value: ")", position: i });
      i++;
      continue;
    }

    // Quoted phrase
    if (query[i] === '"') {
      const start = i;
      i++; // skip opening quote
      let phrase = "";
      while (i < query.length && query[i] !== '"') {
        phrase += query[i];
        i++;
      }
      if (i < query.length) i++; // skip closing quote
      tokens.push({ type: "PHRASE", value: phrase, position: start });
      continue;
    }

    // Word (operator or term)
    const start = i;
    let word = "";
    while (i < query.length && !/[\s()"]/.test(query[i]!)) {
      word += query[i];
      i++;
    }

    const upper = word.toUpperCase();
    if (upper === "AND") {
      tokens.push({ type: "AND", value: "AND", position: start });
    } else if (upper === "OR") {
      tokens.push({ type: "OR", value: "OR", position: start });
    } else if (upper === "NOT") {
      tokens.push({ type: "NOT", value: "NOT", position: start });
    } else {
      tokens.push({ type: "TERM", value: word, position: start });
    }
  }

  tokens.push({ type: "EOF", value: "", position: query.length });
  return tokens;
}

// ============================================
// AST Nodes
// ============================================

export type ASTNode =
  | { type: "term"; value: string }
  | { type: "phrase"; value: string }
  | { type: "and"; left: ASTNode; right: ASTNode }
  | { type: "or"; left: ASTNode; right: ASTNode }
  | { type: "not"; operand: ASTNode };

// ============================================
// Recursive Descent Parser
// ============================================
//
// Grammar:
//   expression = orExpr
//   orExpr     = andExpr ("OR" andExpr)*
//   andExpr    = unaryExpr (("AND" | implicit-AND) unaryExpr)*
//   unaryExpr  = "NOT" unaryExpr | primary
//   primary    = "(" expression ")" | PHRASE | TERM

class Parser {
  private tokens: Token[];
  private pos: number;

  constructor(tokens: Token[]) {
    this.tokens = tokens;
    this.pos = 0;
  }

  parse(): ASTNode {
    const ast = this.orExpr();
    if (this.peek().type !== "EOF") {
      throw new Error(`Unexpected token at position ${this.peek().position}: ${this.peek().value}`);
    }
    return ast;
  }

  private peek(): Token {
    return this.tokens[this.pos]!;
  }

  private advance(): Token {
    const token = this.tokens[this.pos]!;
    this.pos++;
    return token;
  }

  private expect(type: TokenType): Token {
    const token = this.peek();
    if (token.type !== type) {
      throw new Error(`Expected ${type} but got ${token.type} at position ${token.position}`);
    }
    return this.advance();
  }

  // orExpr = andExpr ("OR" andExpr)*
  private orExpr(): ASTNode {
    let left = this.andExpr();

    while (this.peek().type === "OR") {
      this.advance();
      const right = this.andExpr();
      left = { type: "or", left, right };
    }

    return left;
  }

  // andExpr = unaryExpr (("AND" | implicit-AND) unaryExpr)*
  //
  // Implicit AND: two adjacent terms/phrases without an explicit operator
  // are treated as AND. E.g., "dry eye driving" = "dry eye" AND "driving"
  private andExpr(): ASTNode {
    let left = this.unaryExpr();

    while (this.peek().type === "AND" || this.isImplicitAnd()) {
      if (this.peek().type === "AND") {
        this.advance();
      }
      // else: implicit AND — just advance past no token
      const right = this.unaryExpr();
      left = { type: "and", left, right };
    }

    return left;
  }

  // Check for implicit AND between two terms/phrases
  private isImplicitAnd(): boolean {
    const current = this.peek();
    const prevIsTermOrPhrase = current.type === "TERM" || current.type === "PHRASE";
    const notAtStart = this.pos > 0;
    const prevToken = this.tokens[this.pos - 1];
    const prevIsTermOrPhraseOrParen = prevToken &&
      (prevToken.type === "TERM" || prevToken.type === "PHRASE" || prevToken.type === "RPAREN");

    return prevIsTermOrPhraseOrParen && prevIsTermOrPhrase && !this.isBooleanOp(current);
  }

  private isBooleanOp(token: Token): boolean {
    return token.type === "AND" || token.type === "OR" || token.type === "NOT";
  }

  // unaryExpr = "NOT" unaryExpr | primary
  private unaryExpr(): ASTNode {
    if (this.peek().type === "NOT") {
      this.advance();
      const operand = this.unaryExpr();
      return { type: "not", operand };
    }
    return this.primary();
  }

  // primary = "(" expression ")" | PHRASE | TERM
  private primary(): ASTNode {
    const token = this.peek();

    if (token.type === "LPAREN") {
      this.advance();
      const expr = this.orExpr();
      this.expect("RPAREN");
      return expr;
    }

    if (token.type === "PHRASE") {
      this.advance();
      return { type: "phrase", value: token.value };
    }

    if (token.type === "TERM") {
      this.advance();
      return { type: "term", value: token.value };
    }

    throw new Error(`Unexpected token at position ${token.position}: ${token.value || token.type}`);
  }
}

export function parse(query: string): ASTNode {
  const tokens = tokenize(query);
  const parser = new Parser(tokens);
  return parser.parse();
}

// ============================================
// Source-Specific Compilers
// ============================================

/**
 * Compile AST to PubMed E-utilities query syntax.
 * Uses [MeSH] for known terms, [All Fields] for free text.
 * Supports AND, OR, NOT, parentheses, quotes.
 */
export function compilePubMed(ast: ASTNode): string {
  switch (ast.type) {
    case "term":
      return `"${ast.value}"[All Fields]`;
    case "phrase":
      return `"${ast.value}"[All Fields]`;
    case "and":
      return `(${compilePubMed(ast.left)} AND ${compilePubMed(ast.right)})`;
    case "or":
      return `(${compilePubMed(ast.left)} OR ${compilePubMed(ast.right)})`;
    case "not":
      return `NOT ${compilePubMed(ast.operand)}`;
  }
}

/**
 * Compile AST to OpenAlex search syntax.
 * OpenAlex uses natural language search with filter operators.
 * Boolean operators work in `default.search` parameter.
 */
export function compileOpenAlex(ast: ASTNode): string {
  switch (ast.type) {
    case "term":
      return ast.value;
    case "phrase":
      return `"${ast.value}"`;
    case "and":
      return `${compileOpenAlex(ast.left)} ${compileOpenAlex(ast.right)}`;
    case "or":
      return `${compileOpenAlex(ast.left)} OR ${compileOpenAlex(ast.right)}`;
    case "not":
      return `NOT ${compileOpenAlex(ast.operand)}`;
  }
}

/**
 * Compile AST to Crossref query syntax.
 * Crossref uses a simplified query syntax.
 * Quoted phrases, AND/OR/NOT operators.
 */
export function compileCrossref(ast: ASTNode): string {
  switch (ast.type) {
    case "term":
      return ast.value;
    case "phrase":
      return `"${ast.value}"`;
    case "and":
      return `${compileCrossref(ast.left)} AND ${compileCrossref(ast.right)}`;
    case "or":
      return `${compileCrossref(ast.left)} OR ${compileCrossref(ast.right)}`;
    case "not":
      return `${compileCrossref(ast.operand)}`;
  }
}

/**
 * Compile AST to Semantic Scholar query syntax.
 * S2 uses a simple search string. Boolean support is limited.
 * For complex queries, join with spaces (S2 does its own matching).
 */
export function compileSemanticScholar(ast: ASTNode): string {
  switch (ast.type) {
    case "term":
      return ast.value;
    case "phrase":
      return `"${ast.value}"`;
    case "and":
      return `${compileSemanticScholar(ast.left)} ${compileSemanticScholar(ast.right)}`;
    case "or":
      return `${compileSemanticScholar(ast.left)} OR ${compileSemanticScholar(ast.right)}`;
    case "not":
      return `NOT ${compileSemanticScholar(ast.operand)}`;
  }
}

/**
 * Compile AST to ERIC query syntax using the controlled vocabulary crosswalk.
 * ERIC uses its own Thesaurus descriptors. Terms are expanded via the crosswalk
 * to include ERIC descriptors and synonyms, maximizing recall without sacrificing
 * precision. Regional overlays handle localized terminology.
 */
export function compileERIC(ast: ASTNode, crosswalk?: { expand(term: string, region?: string): string[] }, region?: string): string {
  switch (ast.type) {
    case "term": {
      if (crosswalk) {
        const expanded = crosswalk.expand(ast.value, region);
        if (expanded.length > 1) {
          return `(${expanded.map(t => `"${t}"`).join(" OR ")})`;
        }
      }
      return `"${ast.value}"`;
    }
    case "phrase": {
      if (crosswalk) {
        const expanded = crosswalk.expand(ast.value, region);
        if (expanded.length > 1) {
          return `(${expanded.map(t => `"${t}"`).join(" OR ")})`;
        }
      }
      return `"${ast.value}"`;
    }
    case "and":
      return `(${compileERIC(ast.left, crosswalk, region)} AND ${compileERIC(ast.right, crosswalk, region)})`;
    case "or":
      return `(${compileERIC(ast.left, crosswalk, region)} OR ${compileERIC(ast.right, crosswalk, region)})`;
    case "not":
      return `NOT ${compileERIC(ast.operand, crosswalk, region)}`;
  }
}

/**
 * Compile AST to DOAJ query syntax using the controlled vocabulary crosswalk.
 * DOAJ supports simple search with AND/OR operators.
 * Subject terms are expanded via the crosswalk.
 */
export function compileDOAJ(ast: ASTNode, crosswalk?: { expand(term: string, region?: string): string[] }, region?: string): string {
  switch (ast.type) {
    case "term": {
      if (crosswalk) {
        const expanded = crosswalk.expand(ast.value, region);
        if (expanded.length > 1) {
          return `(${expanded.map(t => `"${t}"`).join(" OR ")})`;
        }
      }
      return `"${ast.value}"`;
    }
    case "phrase": {
      if (crosswalk) {
        const expanded = crosswalk.expand(ast.value, region);
        if (expanded.length > 1) {
          return `(${expanded.map(t => `"${t}"`).join(" OR ")})`;
        }
      }
      return `"${ast.value}"`;
    }
    case "and":
      return `(${compileDOAJ(ast.left, crosswalk, region)} AND ${compileDOAJ(ast.right, crosswalk, region)})`;
    case "or":
      return `(${compileDOAJ(ast.left, crosswalk, region)} OR ${compileDOAJ(ast.right, crosswalk, region)})`;
    case "not":
      return `NOT ${compileDOAJ(ast.operand, crosswalk, region)}`;
  }
}

// ============================================
// Master Compiler
// ============================================

export type SourceCompiler = (ast: ASTNode) => string;
export type CrosswalkCompiler = (ast: ASTNode, crosswalk?: { expand(term: string, region?: string): string[] }, region?: string) => string;

export const COMPILERS: Record<string, SourceCompiler> = {
  pubmed: compilePubMed,
  openalex: compileOpenAlex,
  crossref: compileCrossref,
  semantic_scholar: compileSemanticScholar,
  eric: (ast) => compileERIC(ast),
  doaj: (ast) => compileDOAJ(ast),
};

export const CROSSWALK_COMPILERS: Record<string, CrosswalkCompiler> = {
  eric: compileERIC,
  doaj: compileDOAJ,
};

/**
 * Parse a raw query string and compile it for all requested sources.
 * This is the single entry point: parse once, compile many.
 */
export function parseAndCompile(
  rawQuery: string,
  sources: string[],
): Map<string, string> {
  const ast = parse(rawQuery);
  const compiled = new Map<string, string>();

  for (const source of sources) {
    const compiler = COMPILERS[source];
    if (compiler) {
      compiled.set(source, compiler(ast));
    }
  }

  return compiled;
}

/**
 * Parse and compile with crosswalk expansion for specialized sources.
 * For ERIC/DOAJ, terms are expanded via the controlled vocabulary crosswalk.
 */
export function parseAndCompileWithCrosswalk(
  rawQuery: string,
  sources: string[],
  crosswalks: Map<string, { expand(term: string, region?: string): string[] }>,
  region?: string,
): Map<string, string> {
  const ast = parse(rawQuery);
  const compiled = new Map<string, string>();

  for (const source of sources) {
    const crosswalkCompiler = CROSSWALK_COMPILERS[source];
    if (crosswalkCompiler) {
      const crosswalk = crosswalks.get(source);
      compiled.set(source, crosswalkCompiler(ast, crosswalk, region));
    } else {
      const compiler = COMPILERS[source];
      if (compiler) {
        compiled.set(source, compiler(ast));
      }
    }
  }

  return compiled;
}

/**
 * Get the AST as a human-readable string for debugging / transparency.
 */
export function astToString(ast: ASTNode, depth: number = 0): string {
  const indent = "  ".repeat(depth);
  switch (ast.type) {
    case "term":
      return `${indent}TERM: "${ast.value}"`;
    case "phrase":
      return `${indent}PHRASE: "${ast.value}"`;
    case "and":
      return `${indent}AND:\n${astToString(ast.left, depth + 1)}\n${astToString(ast.right, depth + 1)}`;
    case "or":
      return `${indent}OR:\n${astToString(ast.left, depth + 1)}\n${astToString(ast.right, depth + 1)}`;
    case "not":
      return `${indent}NOT:\n${astToString(ast.operand, depth + 1)}`;
  }
}

// ============================================
// Local Intersection Logic
// ============================================
//
// Some sources (OpenAlex, Semantic Scholar) cannot faithfully replicate
// a rigid Boolean AND intersection. When the query contains AND operators,
// we pull the broader OR superset from those sources and perform the
// exact Boolean intersection locally on our backend.

/**
 * Check if an AST contains any AND operators (explicit or implicit).
 */
export function hasAndOperators(ast: ASTNode): boolean {
  if (ast.type === "and") return true;
  if (ast.type === "or") return hasAndOperators(ast.left) || hasAndOperators(ast.right);
  if (ast.type === "not") return hasAndOperators(ast.operand);
  return false;
}

/**
 * Convert AND operators to OR in the AST.
 * This produces the superset: all papers matching ANY clause.
 */
export function convertAndToOr(ast: ASTNode): ASTNode {
  switch (ast.type) {
    case "term":
    case "phrase":
      return ast;
    case "and":
      // Convert AND to OR
      return {
        type: "or",
        left: convertAndToOr(ast.left),
        right: convertAndToOr(ast.right),
      };
    case "or":
      return {
        type: "or",
        left: convertAndToOr(ast.left),
        right: convertAndToOr(ast.right),
      };
    case "not":
      return { type: "not", operand: convertAndToOr(ast.operand) };
  }
}

/**
 * Evaluate an AST against a title string.
 * Returns true if the title matches the query logic.
 */
export function evaluateAST(ast: ASTNode, title: string | string[] | null | undefined): boolean {
  // Handle non-string inputs
  let str: string;
  if (!title) {
    str = "";
  } else if (Array.isArray(title)) {
    str = title[0] ?? "";
  } else if (typeof title === "string") {
    str = title;
  } else {
    str = String(title);
  }
  const lower = str.toLowerCase();

  switch (ast.type) {
    case "term":
      return lower.includes(ast.value.toLowerCase());
    case "phrase":
      return lower.includes(ast.value.toLowerCase());
    case "and":
      return evaluateAST(ast.left, title) && evaluateAST(ast.right, title);
    case "or":
      return evaluateAST(ast.left, title) || evaluateAST(ast.right, title);
    case "not":
      return !evaluateAST(ast.operand, title);
  }
}

// ============================================
// Local Intersection Compilation
// ============================================

// Sources that cannot faithfully handle Boolean AND
const AND_UNSAFE_SOURCES = new Set(["openalex", "semantic_scholar"]);

/**
 * Compile queries for local intersection.
 * Returns two maps: one for the source (superset) and one for local evaluation.
 */
export function compileForLocalIntersection(
  rawQuery: string,
  sources: string[],
): {
  sourceQueries: Map<string, string>;
  ast: ASTNode;
  needsLocalIntersection: boolean;
  andUnsafeSources: string[];
} {
  const ast = parse(rawQuery);
  const needsAnd = hasAndOperators(ast);
  const andUnsafe = sources.filter(s => AND_UNSAFE_SOURCES.has(s) && needsAnd);

  const sourceQueries = new Map<string, string>();

  for (const source of sources) {
    const compiler = COMPILERS[source];
    if (!compiler) continue;

    if (andUnsafe.includes(source)) {
      // Pull superset: convert AND to OR
      const supersetAst = convertAndToOr(ast);
      sourceQueries.set(source, compiler(supersetAst));
    } else {
      // Use native syntax
      sourceQueries.set(source, compiler(ast));
    }
  }

  return {
    sourceQueries,
    ast,
    needsLocalIntersection: andUnsafe.length > 0,
    andUnsafeSources: andUnsafe,
  };
}
