// parler_slug_autofill.js - С ТРАНСЛИТЕРАЦИЕЙ
document.addEventListener("DOMContentLoaded", function () {
  console.log("=== PARLER SLUG AUTOFILL WITH TRANSLIT ===");

  function createSlug(text) {
    if (!text) return "";

    const translitMap = {
      а: "a",
      б: "b",
      в: "v",
      г: "g",
      д: "d",
      е: "e",
      ё: "yo",
      ж: "zh",
      з: "z",
      и: "i",
      й: "y",
      к: "k",
      л: "l",
      м: "m",
      н: "n",
      о: "o",
      п: "p",
      р: "r",
      с: "s",
      т: "t",
      у: "u",
      ф: "f",
      х: "h",
      ц: "ts",
      ч: "ch",
      ш: "sh",
      щ: "sch",
      ъ: "",
      ы: "y",
      ь: "",
      э: "e",
      ю: "yu",
      я: "ya",
      " ": "-",
      _: "_",
      "-": "-",
    };

    return text
      .toLowerCase()
      .trim()
      .split("")
      .map(
        (char) => translitMap[char] || (char.match(/[a-z0-9_-]/) ? char : ""),
      )
      .join("")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "");
  }

  const nameField = document.querySelector('input[name="name"]');
  const slugField = document.querySelector('input[name="slug"]');

  if (nameField && slugField) {
    console.log("Fields found, setting up autofill...");

    nameField.addEventListener("input", function () {
      if (!slugField.value) {
        const newSlug = createSlug(this.value);
        slugField.value = newSlug;
        console.log("Auto-filled slug:", newSlug);
      }
    });

    if (nameField.value && !slugField.value) {
      slugField.value = createSlug(nameField.value);
    }
  }
});
