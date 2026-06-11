import type { Plugin } from 'vite';

/** Remove misplaced PURE annotations that Rolldown warns on in @vueuse/core@14.3.0. */
export function vueusePureAnnotationFix(): Plugin {
  return {
    name: 'vueuse-pure-annotation-fix',
    transform(code, id) {
      if (!id.includes('@vueuse/core')) {
        return null;
      }

      const cleaned = code
        .replace(/^\/\* #__PURE__ \*\/\r?\n/gm, '')
        .replace(/\(\/\* #__PURE__ \*\/ /g, '(');

      if (cleaned === code) {
        return null;
      }

      return { code: cleaned, map: null };
    },
  };
}
