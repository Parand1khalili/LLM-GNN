# GraphScope design

Approved direction from the design discussion, 2026-11-06.

Two primary colors: petroleum #205B60 and terracotta #B4472D. Gold #D69A28 is a focus accent, never small text on paper. Paper #F5F2EA, ink #222C2D, neutral lines #D8D3C8. B1 is petroleum; Narrative is terracotta. Selection uses a gold ring. Shape, text and position supplement color.

Operate: Explore, Prediction Desk and Agents. Read: Overview, Methods, Experiments and Workflow. Keep graph controls compact, comparison columns aligned, methods as a reading index and workflow as a connected sequence instead of pastel cards. Remove decorative page numbering and italic hero emphasis. Preserve serif scientific titles and readable sans text.

Agents uses a responsibility score and an adjacent input/output inspector. Numbers indicate reading order, not an assertion that every node executes every role. Explicitly label conditional comparison, independent L2 and unavailable node outcomes. On mobile, roles become a compact two-column index and detail follows below.

Implementation: src/atlas-design.css extends the existing layered stylesheet without replacing research components or data contracts. No new dependency or remote font/asset.


2026-11-14 workbench refinement: `core.css` sets16px body,14px labels,13px captions,44px controls,tabular data and reduced motion. New default selected-method workflow uses a scientific branch diagram and interactive stage contracts. Final benchmark has zero-to100accuracy scale with exact tables;historical studies remain in disclosure. Full graph has78component structural layout with topology-only display partitions;no class geometry claim. Graph mobile defaults to node list. Tests/captures cover1440x900,768x1024,390x844;see docs/GRAPH_SCOPE_UX_QA.md for limitations.
