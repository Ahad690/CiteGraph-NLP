/**
 * citeproc ships no TypeScript declarations.
 *
 * The surface used here is small and verified by probe rather than by a type
 * file, so this declares only what is actually called. The calling convention is
 * unusual and worth stating, because none of it appears in the package's
 * README: `updateItems` takes item IDS rather than item objects, `sys.retrieveItem`
 * must return the item, `setOutputFormat` accepts only "html", "text" and "rtf",
 * and `makeBibliography` returns a layout object followed by an object whose keys
 * are line indexes. Getting any of these wrong produces a runtime error that
 * names a different component -- `updateItems` with objects fails as
 * "Cannot read properties of null (reading 'language')" -- so the shapes are
 * recorded here where the next reader will see them.
 */

declare module "citeproc" {
  export type CslItemType = "article-journal" | string;

  export interface EngineOptions {
    retrieveLocale: (lang: string) => string;
    retrieveItem: (id: string) => unknown;
  }

  /**
   * The module's default export is the CSL namespace itself, and the engine is
   * a property on it -- `new CSL.Engine(...)`, not `new CSL(...)`. Declaring the
   * default as a class with a static made that call a type error even though it
   * is the documented usage.
   */
  const CSL: {
    Engine: new (sys: EngineOptions, styleXml: string, lang: string) => Engine;
  };
  export default CSL;

  export interface Engine {
    setOutputFormat(mode: "html" | "text" | "rtf"): void;
    /** Takes item ids, not item objects. */
    updateItems(ids: string[]): void;
    /**
     * The first object is layout metadata whose `entry_ids` maps each rendered
     * entry back to its item. The remaining objects hold the rendered lines,
     * keyed by line index -- several keys in one object, not one object per line.
     */
    makeBibliography(): Array<Record<string, unknown>>;
  }
}
