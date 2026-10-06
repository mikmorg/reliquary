# Break-glass runbook (DRILL copy)

> Print this on paper. It is the only help you get. Nobody will answer questions during the drill.
> This is a practice run with practice keys and practice photos. Nothing you do can break the real backups.
>
> Draft for the D2-S3 drill only. The real printed runbook is co-owned by D2 and E7 and will be
> rewritten from what this drill teaches us.

**What you are doing:** getting 10 photos back from a backup disk, using two of the three
"share cards" and a computer. You need about an hour. Write down the time when you start.

**You need:**

- The **DRILL disk** (a USB disk labelled "DRILL").
- **Two** of the three **share cards**. Each card has a long list of words on it.
- The **recovery computer** prepared for this drill (it already has two programs: `shamir` and `age`).
- This runbook, a pen, and the observer's timer.

The 10 photos to recover are listed on the last page ("Your 10 photos").

---

## Step 1. Start

1. Write the time here: ________
2. Plug the DRILL disk into the recovery computer.
3. Open the **Terminal** program. (On a Mac: press Command and Space, type `Terminal`, press Enter.
   On Linux: find "Terminal" in the menu.)

**You should see:** a window with a line of text ending in `$` or `%`. This is where you type commands.
Type each command exactly as printed, then press **Enter**.

## Step 2. Go to the disk

Type:

```
cd /Volumes/DRILL
```

(On Linux the observer's sheet gives the path instead of `/Volumes/DRILL`.)

**You should see:** nothing, or the same `$` line again. That means it worked.

## Step 3. Put the share cards together

Type:

```
shamir recover
```

**You should see:** `Enter a recovery share:`

1. Type **all the words** from the first card, with one space between words. Press Enter.
   The words must be in the order they are printed. Capital letters do not matter.
2. **You should see:** `1 of 2 shares needed`. Type the words from the second card. Press Enter.
3. **You should see:** `SUCCESS!` and a line `Your master secret is:` followed by a long mix of numbers
   and the letters a to f.

If you see an error about a checksum or a word, one word is mistyped. Check the card and type that card again.

Leave this window open. You need the long secret in the next step.

## Step 4. Unlock the recovery key

Type:

```
age -d -o ~/recovery-key.txt recovery/recovery-identity.age
```

**You should see:** `Enter passphrase:`

Copy the long secret from Step 3 (select it with the mouse, then copy), paste it here, and press Enter.
Nothing appears on the screen while you paste. That is normal.

**You should see:** the `$` line again, with no error.

If you see `incorrect passphrase`, the secret was not pasted completely. Try again.

## Step 5. Check that it is the right key

Type:

```
age-keygen -y ~/recovery-key.txt
```

**You should see:** a very long line starting with `age1`.
Compare its **start** and **end** with the line "Recovery key check" on the share card.
If they do not match, stop and write down what you see.

## Step 6. Open the list of photos

Type:

```
age -d -i ~/recovery-key.txt store/catalog.tsv.age > ~/catalog.txt
```

Then open the file `catalog.txt` in your home folder with a text editor.

**You should see:** a list. Each line has a file name, then a long code (the "object" code), then numbers.
Find the 10 photos listed on the last page of this runbook. Next to each, write the first 6 characters of its code.

## Step 7. Get each photo back

For **each** of the 10 photos, type this command, replacing `CODE` with the photo's full code from the list
and `NAME` with its file name:

```
age -d -i ~/recovery-key.txt -o ~/Desktop/NAME store/objects/CODE.age
```

**You should see:** the photo appear on your Desktop. Open it. Tick it off on the last page.

## Step 8. Clean up

Type:

```
rm ~/recovery-key.txt ~/catalog.txt
```

Write the time here: ________. Hand this sheet and the cards back to the observer.

---

## Your 10 photos

(The owner fills in the 10 file names before printing.)

| # | File name | First 6 characters of its code | Opened? |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |
| 6 | | | |
| 7 | | | |
| 8 | | | |
| 9 | | | |
| 10 | | | |
