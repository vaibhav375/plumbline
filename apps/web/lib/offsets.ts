/**
 * The checker's offsets count Unicode code points (Python string indices); JavaScript strings
 * count UTF-16 units, where an emoji is 2. Convert before slicing, or highlights after an emoji
 * land one character off (Task 4 note).
 */
export function utf16Index(text: string, codePoint: number): number {
  let units = 0;
  let cp = 0;
  for (const ch of text) {
    if (cp === codePoint) break;
    units += ch.length;
    cp += 1;
  }
  return units;
}
