// stubgen hollows out Go source files in place: every function body is replaced
// by a panic, while types, constants, variables and all signatures are kept
// exactly as they were.  That is the carve-out: the contract survives, the
// implementation does not.
//
//	go run stubgen.go promql/engine.go promql/functions.go ...
//
// Unused imports are left alone on purpose — the caller fixes them from the
// compiler's own error messages (fix_imports in controls.sh), which is more
// reliable than guessing which import only the deleted bodies needed.
package main

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/printer"
	"go/token"
	"os"
	"strconv"
)

const marker = "carved out: re-implement this"

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: stubgen <file.go> [file.go ...]")
		os.Exit(2)
	}
	for _, path := range os.Args[1:] {
		if err := hollow(path); err != nil {
			fmt.Fprintf(os.Stderr, "stubgen %s: %v\n", path, err)
			os.Exit(1)
		}
	}
}

func hollow(path string) error {
	fset := token.NewFileSet()
	f, err := parser.ParseFile(fset, path, nil, parser.ParseComments)
	if err != nil {
		return err
	}

	funcs, bodies := 0, 0
	for _, decl := range f.Decls {
		fn, ok := decl.(*ast.FuncDecl)
		if !ok {
			continue
		}
		funcs++
		if fn.Body == nil { // assembly or external linkage
			continue
		}
		bodies++
		fn.Body = stubBody(fn)
		// Doc comments describe behaviour; the whole point is to make the
		// solver derive it from the specification and the tests.
		fn.Doc = nil
	}

	// Comments are attached to the file, not the nodes, so a doc comment
	// cleared above would still be printed.  Drop every comment in the file
	// and print without the comment map.
	f.Comments = nil

	out, err := os.Create(path)
	if err != nil {
		return err
	}
	defer out.Close()
	cfg := printer.Config{Mode: printer.TabIndent, Tabwidth: 8}
	if err := cfg.Fprint(out, fset, f); err != nil {
		return err
	}
	fmt.Printf("stubbed %-45s %3d funcs, %3d bodies removed\n", path, funcs, bodies)
	return nil
}

// stubBody returns the zero value for every result instead of panicking.
//
// Panicking is the obvious choice and it is wrong here: prometheus initialises
// `var ratioSampler = NewHashRatioSampler()` at package scope, so a panicking
// stub dies during package init and the test binary never starts.  The echo
// carve-out hit the same wall — the negative control then reads "no tests ran"
// instead of "tests failed", which hides whether the starting tree is even
// runnable.  Zero values keep the tree alive so the solver gets real assertion
// failures to work against.
func stubBody(fn *ast.FuncDecl) *ast.BlockStmt {
	res := fn.Type.Results
	if res == nil || len(res.List) == 0 {
		return &ast.BlockStmt{}
	}
	// Named results: a naked return already yields the zero values.
	if len(res.List[0].Names) > 0 {
		return &ast.BlockStmt{List: []ast.Stmt{&ast.ReturnStmt{}}}
	}
	var stmts []ast.Stmt
	var names []ast.Expr
	i := 0
	for _, field := range res.List {
		n := len(field.Names)
		if n == 0 {
			n = 1
		}
		for j := 0; j < n; j++ {
			name := ast.NewIdent("r" + strconv.Itoa(i))
			i++
			stmts = append(stmts, &ast.DeclStmt{Decl: &ast.GenDecl{
				Tok: token.VAR,
				Specs: []ast.Spec{&ast.ValueSpec{
					Names: []*ast.Ident{name},
					Type:  field.Type,
				}},
			}})
			names = append(names, name)
		}
	}
	stmts = append(stmts, &ast.ReturnStmt{Results: names})
	return &ast.BlockStmt{List: stmts}
}

func funcName(fn *ast.FuncDecl) string {
	if fn.Recv != nil && len(fn.Recv.List) > 0 {
		return recvName(fn.Recv.List[0].Type) + "." + fn.Name.Name
	}
	return fn.Name.Name
}

func recvName(e ast.Expr) string {
	switch t := e.(type) {
	case *ast.StarExpr:
		return recvName(t.X)
	case *ast.Ident:
		return t.Name
	case *ast.IndexExpr:
		return recvName(t.X)
	case *ast.IndexListExpr:
		return recvName(t.X)
	}
	return "?"
}
