from neo4j import GraphDatabase

d = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "123258789"))

# Check each xinggraph database
for dbname in ["xinggraph106957b5ff3751779c86d5a4f2f7b762", "xinggraphccd5181a50be58289bf26d6aa8998f39", "xinggraphd178fa8d210856e99b6be8ab650d8d5a"]:
    print(f"\n=== {dbname} ===")
    with d.session(database=dbname) as s:
        r = s.run("MATCH (n) RETURN labels(n) AS label, count(*) AS cnt ORDER BY cnt DESC")
        results = list(r)
        if not results:
            print("  EMPTY")
        for rec in results:
            print(f"  Node: {rec['label']}: {rec['cnt']}")

        r2 = s.run("MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS cnt ORDER BY cnt DESC")
        results2 = list(r2)
        if not results2:
            print("  No edges")
        for rec in results2:
            print(f"  Edge: {rec['rel']}: {rec['cnt']}")

        # Sample nodes
        r3 = s.run("MATCH (n) RETURN n.name AS name, labels(n) AS labels LIMIT 5")
        print("  Sample nodes:")
        for rec in r3:
            print(f"    {rec['labels']}: {rec['name']}")

d.close()
