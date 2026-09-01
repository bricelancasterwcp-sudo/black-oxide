fn strided_sum(grid: &[i64], start: usize, step: usize, count: usize) -> i64 {
    let mut total = 0;
    for k in 0..count {
        total += grid[start + k * step];
    }
    total
}

fn main() {
    let grid = [4, 9, 2, 3, 5, 7, 8, 1, 6];
    let size = 3;
    let mut sums: Vec<i64> = Vec::new();
    for r in 0..size {
        let s = strided_sum(&grid, r * size, 1, size);
        println!("{}", s);
        sums.push(s);
    }
    for c in 0..size {
        let s = strided_sum(&grid, c, size, size);
        println!("{}", s);
        sums.push(s);
    }
    let diagonal = strided_sum(&grid, 0, size + 1, size);
    let anti = strided_sum(&grid, size - 1, size - 1, size);
    println!("{}", diagonal);
    println!("{}", anti);
    let magic = sums.iter().all(|s| *s == diagonal) && anti == diagonal;
    println!("{}", magic);
}
